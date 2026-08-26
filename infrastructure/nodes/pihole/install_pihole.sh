#!/usr/bin/env bash
# ==============================================================================
# install_pihole.sh — Install Pi-hole v6 (native) on Debian guest ARM64
#
# Run ON the Pi-hole VM (after create_pihole_vm.sh + cloud-init):
#   scp infrastructure/nodes/pihole/install_pihole.sh \
#       infrastructure/nodes/pihole/pihole.toml.example \
#       pi@192.168.1.53:/tmp/
#   ssh -t pi@192.168.1.53 'sudo PIHOLE_WEBPASSWORD="..." bash /tmp/install_pihole.sh'
#
# Or with a pre-seeded toml (password already set):
#   sudo bash /tmp/install_pihole.sh --toml /tmp/pihole.toml
#
# Environment:
#   PIHOLE_WEBPASSWORD  — web UI password (required unless toml already has one)
#   PIHOLE_TOML         — path to pre-seed file (default: beside this script / example)
#   TZ                  — timezone (default Europe/Madrid)
# ==============================================================================
set -euo pipefail

TZ="${TZ:-Europe/Madrid}"
PIHOLE_TOML="${PIHOLE_TOML:-}"
INSTALLER_URL="${INSTALLER_URL:-https://install.pi-hole.net}"
SKIP_GRAVITY=0

usage() {
    sed -n '2,22p' "$0"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --toml)
            PIHOLE_TOML="$2"
            shift 2
            ;;
        --skip-gravity)
            SKIP_GRAVITY=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

die() {
    log "ERROR: $*"
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        die "Run as root (sudo)."
    fi
}

script_dir() {
    local src="${BASH_SOURCE[0]:-$0}"
    cd "$(dirname "$src")" && pwd
}

resolve_toml_source() {
    if [[ -n "$PIHOLE_TOML" ]]; then
        [[ -f "$PIHOLE_TOML" ]] || die "TOML not found: ${PIHOLE_TOML}"
        echo "$PIHOLE_TOML"
        return
    fi
    local dir candidate
    dir="$(script_dir)"
    for candidate in \
        "${dir}/pihole.toml" \
        "${dir}/pihole.toml.example" \
        "/tmp/pihole.toml" \
        "/tmp/pihole.toml.example"
    do
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return
        fi
    done
    die "No pihole.toml(.example) found. Pass --toml PATH or copy the example to /tmp."
}

install_base_packages() {
    log "Installing base packages (qemu-guest-agent, curl, dnsutils)..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq \
        qemu-guest-agent \
        curl \
        wget \
        dnsutils \
        ca-certificates \
        sudo

    timedatectl set-timezone "$TZ" 2>/dev/null || ln -sf "/usr/share/zoneinfo/${TZ}" /etc/localtime

    systemctl enable --now qemu-guest-agent 2>/dev/null || true
    log "Base packages ready. TZ=${TZ}"
}

disable_cloudinit_manage_hosts() {
    # Same anti-pattern as PXVIRT host: cloud-init must not rewrite /etc/hosts.
    local cfg="/etc/cloud/cloud.cfg"
    if [[ -f "$cfg" ]]; then
        if grep -q '^manage_etc_hosts:' "$cfg"; then
            sed -i 's/^manage_etc_hosts:.*/manage_etc_hosts: false/' "$cfg"
        else
            printf '\nmanage_etc_hosts: false\n' >> "$cfg"
        fi
        log "Set manage_etc_hosts: false in ${cfg}"
    fi
}

seed_pihole_toml() {
    local src dest="/etc/pihole/pihole.toml"
    local password="${PIHOLE_WEBPASSWORD:-}"

    src="$(resolve_toml_source)"
    mkdir -p /etc/pihole
    chmod 755 /etc/pihole

    cp "$src" "$dest"
    chmod 644 "$dest"

    if [[ -n "$password" ]]; then
        # Replace placeholder or existing password line under [webserver.api]
        if grep -q 'password\s*=' "$dest"; then
            # Escape for sed: &, \, and |
            local esc
            esc="$(printf '%s' "$password" | sed -e 's/[\\&|]/\\&/g')"
            sed -i "s|^[[:space:]]*password[[:space:]]*=[[:space:]]*.*|  password = \"${esc}\"|" "$dest"
        else
            printf '\n[webserver.api]\n  password = "%s"\n' "$password" >> "$dest"
        fi
        log "Seeded ${dest} with PIHOLE_WEBPASSWORD"
    elif grep -q 'REPLACE_ME' "$dest"; then
        die "Set PIHOLE_WEBPASSWORD or replace REPLACE_ME in ${src} before install."
    else
        log "Using password already present in ${src}"
    fi

    # Ensure Cloudflare upstreams and LOCAL listening (idempotent soft fix)
    if ! grep -q '1.1.1.1' "$dest"; then
        log "WARNING: ${dest} may lack Cloudflare upstreams — check [dns].upstreams"
    fi
}

run_pihole_installer() {
    local tmp_installer
    tmp_installer="$(mktemp)"
    log "Downloading Pi-hole installer from ${INSTALLER_URL}..."
    curl -fsSL "$INSTALLER_URL" -o "$tmp_installer"
    chmod 700 "$tmp_installer"

    log "Running unattended install (requires pre-seeded /etc/pihole/pihole.toml)..."
    # Pi-hole v6: --unattended works when pihole.toml already exists
    bash "$tmp_installer" --unattended
    rm -f "$tmp_installer"
    log "Installer finished."
}

set_password_cli() {
    if [[ -n "${PIHOLE_WEBPASSWORD:-}" ]] && command -v pihole &>/dev/null; then
        # Ensure UI password matches env even if toml hashing differed
        pihole setpassword "${PIHOLE_WEBPASSWORD}" 2>/dev/null \
            || pihole -a -p "${PIHOLE_WEBPASSWORD}" 2>/dev/null \
            || true
    fi
}

update_gravity() {
    if [[ "$SKIP_GRAVITY" -eq 1 ]]; then
        log "Skipping gravity update (--skip-gravity)."
        return
    fi
    log "Updating gravity blocklists (default StevenBlack)..."
    pihole -g
}

verify_dns() {
    log "Verifying local DNS..."
    if dig +time=3 +tries=1 @127.0.0.1 google.com +short | grep -qE '^[0-9.]+$'; then
        log "OK: dig @127.0.0.1 google.com resolved."
    else
        log "WARNING: dig @127.0.0.1 google.com failed — check pihole-FTL status."
        systemctl --no-pager -l status pihole-FTL || true
    fi
}

print_next_steps() {
    local ip
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || echo '192.168.1.53')"
    cat <<EOF

=== Pi-hole install complete ===
Admin UI:  http://${ip}/admin
DNS test:  dig @${ip} google.com
Block test: dig @${ip} doubleclick.net

Cutover (do NOT do on day 0 — see docs/pihole.md):
  1. Reserva DHCP ${ip} en el router
  2. Probar solo Mac / un cliente
  3. DNS LAN del router → ${ip} (secundario 1.1.1.1 solo en burn-in)
  4. Rollback: DNS router → ISP / 1.1.1.1

Do NOT point this VM's resolv.conf at itself (DNS loop).
Upstream remains Cloudflare (1.1.1.1 / 1.0.0.1).
EOF
}

main() {
    require_root
    log "=== Pi-hole v6 native install ==="
    install_base_packages
    disable_cloudinit_manage_hosts
    seed_pihole_toml
    run_pihole_installer
    set_password_cli
    update_gravity
    verify_dns
    print_next_steps
}

main "$@"
