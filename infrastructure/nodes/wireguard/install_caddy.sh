#!/usr/bin/env bash
# ==============================================================================
# install_caddy.sh — Caddy reverse proxy with Cloudflare DNS-01 on WireGuard VM
#
# Run on the guest (192.168.1.55), as root, AFTER install_wireguard.sh:
#   bash install_caddy.sh
#
# DNS for waynehomelab.com is on Cloudflare (Porkbun is registrar only).
# ACME DNS-01 requires github.com/caddy-dns/cloudflare — not porkbun.
#
# Strategy (no Go/xcaddy on the 512 MiB VM):
#   1. Install official Caddy Debian package (systemd unit + paths)
#   2. Replace /usr/bin/caddy with linux/arm64 build that includes
#      github.com/caddy-dns/cloudflare (download API or pre-built CADDY_BINARY)
#   3. Install Caddyfile + EnvironmentFile for Cloudflare API token
#
# Prerequisites:
#   - WireGuard up (10.44.0.1 on wg0)
#   - /etc/caddy/cloudflare.env with CF_API_TOKEN (from cloudflare.env.example)
#   - OR set CF_API_TOKEN in the environment
#
# Cloudflare API token permissions (zone waynehomelab.com only):
#   Zone → Zone:Read , Zone → DNS:Edit
#
# Optional:
#   CADDY_BINARY=/path/to/caddy   # skip download; use local linux/arm64 binary
#   CADDYFILE_SRC=/path/to/Caddyfile
# ==============================================================================
set -euo pipefail

CADDY_DOWNLOAD_URL="${CADDY_DOWNLOAD_URL:-https://caddyserver.com/api/download?os=linux&arch=arm64&p=github.com%2Fcaddy-dns%2Fcloudflare}"
CADDY_BINARY="${CADDY_BINARY:-}"
CADDYFILE_SRC="${CADDYFILE_SRC:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CF_ENV="/etc/caddy/cloudflare.env"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

die() {
  log "ERROR: $*"
  exit 1
}

require_root() {
  if [[ ${EUID} -ne 0 ]]; then
    die "run as root (sudo)"
  fi
}

install_caddy_package() {
  if command -v caddy >/dev/null 2>&1 && dpkg -l caddy 2>/dev/null | grep -q '^ii'; then
    log "Caddy package already installed."
    return
  fi

  log "Installing Caddy from official Debian package (Cloudsmith)..."
  apt-get update -qq
  apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl

  if [[ ! -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg ]]; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
      | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  fi
  if [[ ! -f /etc/apt/sources.list.d/caddy-stable.list ]]; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
      | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  fi
  chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  chmod o+r /etc/apt/sources.list.d/caddy-stable.list

  apt-get update -qq
  apt-get install -y -qq caddy
  log "Caddy package installed (stock binary; will replace with Cloudflare build)."
}

install_cloudflare_binary() {
  local tmp_bin="/tmp/caddy-cloudflare-arm64"
  local dest="/usr/bin/caddy"

  if [[ -n "${CADDY_BINARY}" ]]; then
    [[ -f "${CADDY_BINARY}" ]] || die "CADDY_BINARY not found: ${CADDY_BINARY}"
    log "Using pre-built binary: ${CADDY_BINARY}"
    if [[ "${CADDY_BINARY}" -ef "${tmp_bin}" ]] || [[ "${CADDY_BINARY}" == "${tmp_bin}" ]]; then
      : # already at staging path
    else
      cp "${CADDY_BINARY}" "${tmp_bin}"
    fi
  else
    log "Downloading Caddy linux/arm64 + cloudflare module..."
    log "URL: ${CADDY_DOWNLOAD_URL}"
    log "Note: download API has no SLA; if this fails, build on Mac:"
    log "  GOOS=linux GOARCH=arm64 xcaddy build --with github.com/caddy-dns/cloudflare"
    log "  scp caddy pi@192.168.1.55:/tmp/ && sudo CADDY_BINARY=/tmp/caddy bash install_caddy.sh"

    if ! curl -fsSL --connect-timeout 30 --max-time 300 \
      -o "${tmp_bin}" "${CADDY_DOWNLOAD_URL}"; then
      die "Download failed. Build with xcaddy on Mac M3 and re-run with CADDY_BINARY=..."
    fi

    if head -c 1 "${tmp_bin}" | grep -q '{'; then
      die "Download returned JSON/error, not a binary. Use xcaddy fallback."
    fi
  fi

  chmod 755 "${tmp_bin}"
  if ! "${tmp_bin}" version >/dev/null 2>&1; then
    die "Downloaded file is not a runnable caddy binary for this arch."
  fi

  set +o pipefail
  if ! "${tmp_bin}" list-modules 2>/dev/null | grep -q 'dns.providers.cloudflare'; then
    set -o pipefail
    die "Binary lacks dns.providers.cloudflare module."
  fi
  set -o pipefail

  systemctl stop caddy 2>/dev/null || true
  if command -v dpkg-divert >/dev/null 2>&1; then
    if [[ ! -e /usr/bin/caddy.stock ]]; then
      dpkg-divert --local --rename --add /usr/bin/caddy 2>/dev/null || true
      if [[ -f /usr/bin/caddy ]] && [[ ! -f /usr/bin/caddy.stock ]]; then
        cp -a /usr/bin/caddy /usr/bin/caddy.stock || true
      fi
    fi
  fi

  install -m 755 "${tmp_bin}" "${dest}"
  rm -f "${tmp_bin}"
  log "Installed Cloudflare-enabled caddy: $(caddy version)"
}

install_cloudflare_env() {
  mkdir -p /etc/caddy

  if [[ -f "${CF_ENV}" ]]; then
    log "Found existing ${CF_ENV}"
  elif [[ -n "${CF_API_TOKEN:-}" ]]; then
    umask 077
    cat > "${CF_ENV}" <<EOF
CF_API_TOKEN=${CF_API_TOKEN}
EOF
    chmod 600 "${CF_ENV}"
    chown caddy:caddy "${CF_ENV}" 2>/dev/null || chown root:root "${CF_ENV}"
    log "Wrote ${CF_ENV} from environment."
  else
    local example="${SCRIPT_DIR}/cloudflare.env.example"
    if [[ -f "${example}" ]]; then
      cp "${example}" "${CF_ENV}"
      chmod 600 "${CF_ENV}"
    fi
    die "Create ${CF_ENV} with a Cloudflare API token (see cloudflare.env.example), then re-run."
  fi

  if grep -q 'REPLACE_ME' "${CF_ENV}"; then
    die "${CF_ENV} still has placeholders. Edit CF_API_TOKEN and re-run."
  fi

  chmod 600 "${CF_ENV}"
  chown caddy:caddy "${CF_ENV}" 2>/dev/null || true
}

install_caddyfile() {
  local src="${CADDYFILE_SRC}"
  if [[ -z "${src}" ]]; then
    if [[ -f "${SCRIPT_DIR}/Caddyfile" ]]; then
      src="${SCRIPT_DIR}/Caddyfile"
    else
      die "No Caddyfile found. Set CADDYFILE_SRC=..."
    fi
  fi

  install -m 644 "${src}" /etc/caddy/Caddyfile
  log "Installed /etc/caddy/Caddyfile from ${src}"
}

configure_systemd_env() {
  mkdir -p /etc/systemd/system/caddy.service.d
  cat > /etc/systemd/system/caddy.service.d/cloudflare.conf <<'EOF'
[Service]
EnvironmentFile=/etc/caddy/cloudflare.env
# Override stock ExecStart: --environ dumps CF_API_TOKEN into the journal.
ExecStart=
ExecStart=/usr/bin/caddy run --config /etc/caddy/Caddyfile
Restart=on-failure
RestartSec=5s
EOF
  # Remove legacy porkbun drop-in if present
  rm -f /etc/systemd/system/caddy.service.d/porkbun.conf
  systemctl daemon-reload
  log "Systemd drop-in: EnvironmentFile=${CF_ENV} (no --environ)"
}

ensure_wg_interface() {
  if ! ip -4 addr show wg0 2>/dev/null | grep -q '10\.44\.0\.1'; then
    log "WARN: wg0 does not have 10.44.0.1 yet. Caddy binds to that address."
    log "Run install_wireguard.sh and ensure wg-quick@wg0 is up before relying on HTTPS."
  else
    log "OK: wg0 has 10.44.0.1 (Caddy bind target)."
  fi
}

enable_service() {
  systemctl enable caddy
  systemctl restart caddy
  sleep 2
  if systemctl is-active --quiet caddy; then
    log "Caddy is active."
  else
    log "Caddy failed to start — check: journalctl -u caddy -n 50 --no-pager"
    systemctl status caddy --no-pager || true
    exit 1
  fi
}

print_summary() {
  log "Caddy ready."
  log "Site: https://ha.waynehomelab.com (only via WireGuard → 10.44.0.1:443)"
  log "Upstream: http://192.168.1.110:8123"
  log "TLS: Let's Encrypt DNS-01 via Cloudflare (no ports 80/443 on WAN)."
  log "Pi-hole local DNS: 10.44.0.1 ha.waynehomelab.com"
  log "HA Network UI: Trust XFF + trusted_proxies = 192.168.1.55"
}

main() {
  require_root
  install_caddy_package
  install_cloudflare_binary
  install_cloudflare_env
  install_caddyfile
  configure_systemd_env
  ensure_wg_interface
  enable_service
  print_summary
}

main "$@"
