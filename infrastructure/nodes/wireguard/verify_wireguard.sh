#!/usr/bin/env bash
# ==============================================================================
# verify_wireguard.sh — Smoke tests for WireGuard VM + private HA HTTPS
#
# Usage (from Mac / LAN host):
#   bash infrastructure/nodes/wireguard/verify_wireguard.sh
#
# Environment:
#   WG_LAN_IP=192.168.1.55
#   WG_VPN_IP=10.44.0.1
#   HA_LAN_URL=http://192.168.1.110:8123
#   HA_VPN_HOST=ha.waynehomelab.com
#   PIHOLE_IP=192.168.1.53
#   SKIP_VPN_HTTPS=1   # skip checks that require active WireGuard tunnel
#
# Exit 0 if LAN critical checks pass. VPN HTTPS is WARN if SKIP_VPN_HTTPS=1
# or tunnel is down.
# ==============================================================================
set -euo pipefail

WG_LAN_IP="${WG_LAN_IP:-192.168.1.55}"
WG_VPN_IP="${WG_VPN_IP:-10.44.0.1}"
HA_LAN_URL="${HA_LAN_URL:-http://192.168.1.110:8123}"
HA_VPN_HOST="${HA_VPN_HOST:-ha.waynehomelab.com}"
PIHOLE_IP="${PIHOLE_IP:-192.168.1.53}"
WG_PORT="${WG_PORT:-51820}"
SKIP_VPN_HTTPS="${SKIP_VPN_HTTPS:-0}"
failed=0
warned=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

need_cmd() {
  command -v "$1" &>/dev/null || {
    log "ERROR: missing command: $1"
    exit 1
  }
}

tcp_closed() {
  # return 0 if port appears closed / filtered from this host
  local host="$1" port="$2"
  if command -v nc &>/dev/null; then
    if nc -z -G 2 "$host" "$port" 2>/dev/null || nc -z -w 2 "$host" "$port" 2>/dev/null; then
      return 1
    fi
    return 0
  fi
  # fallback: curl connect timeout
  if curl -s -o /dev/null --connect-timeout 2 "http://${host}:${port}/" 2>/dev/null; then
    return 1
  fi
  return 0
}

need_cmd curl
need_cmd ping
need_cmd dig

log "=== WireGuard / private HA verify ==="
log "LAN VM: ${WG_LAN_IP} | VPN IP: ${WG_VPN_IP} | HA host: ${HA_VPN_HOST}"

# --- LAN: WireGuard VM reachable ---
if ping -c 1 -W 2 "$WG_LAN_IP" &>/dev/null || ping -c 1 -t 2 "$WG_LAN_IP" &>/dev/null; then
  log "OK: ping ${WG_LAN_IP}"
else
  log "FAIL: ping ${WG_LAN_IP} (VM down? create_wireguard_vm.sh / qm start 102)"
  failed=1
fi

# --- LAN: HA still on HTTP (IoT / Satellite1 path) ---
ha_code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 "${HA_LAN_URL}" || true)"
if [[ -z "$ha_code" || "$ha_code" == "000" ]]; then
  log "FAIL: HA LAN ${HA_LAN_URL} unreachable"
  failed=1
elif [[ "$ha_code" =~ ^[23] || "$ha_code" == "401" || "$ha_code" == "400" ]]; then
  log "OK: HA LAN ${HA_LAN_URL} → HTTP ${ha_code}"
else
  log "WARN: HA LAN ${HA_LAN_URL} → HTTP ${ha_code}"
  warned=1
fi

# --- Security: Caddy must NOT listen on LAN IP :443 ---
if tcp_closed "$WG_LAN_IP" 443; then
  log "OK: ${WG_LAN_IP}:443 closed from LAN (Caddy binds ${WG_VPN_IP} only)"
else
  log "FAIL: ${WG_LAN_IP}:443 is open — Caddy should bind ${WG_VPN_IP} only"
  failed=1
fi

# --- UDP 51820: best-effort (nc -u is unreliable); note only ---
log "INFO: ensure router DNAT UDP ${WG_PORT} → ${WG_LAN_IP} (manual check)"

# --- Pi-hole split DNS ---
if dig +time=3 +tries=1 @"${PIHOLE_IP}" "${HA_VPN_HOST}" >/dev/null 2>&1; then
  ha_ans="$(dig +time=3 +tries=1 +short @"${PIHOLE_IP}" "${HA_VPN_HOST}" | head -n1 || true)"
  if [[ "$ha_ans" == "${WG_VPN_IP}" ]]; then
    log "OK: dig @${PIHOLE_IP} ${HA_VPN_HOST} → ${ha_ans}"
  elif [[ -z "$ha_ans" ]]; then
    log "WARN: Pi-hole has no local DNS for ${HA_VPN_HOST} yet"
    log "  Add: pihole-FTL --config dns.hosts '[\"${WG_VPN_IP} ${HA_VPN_HOST}\"]' (merge carefully)"
    log "  Or UI: Local DNS → ${HA_VPN_HOST} → ${WG_VPN_IP}"
    warned=1
  else
    log "WARN: dig @${PIHOLE_IP} ${HA_VPN_HOST} → ${ha_ans} (expected ${WG_VPN_IP})"
    warned=1
  fi
else
  log "WARN: dig @${PIHOLE_IP} ${HA_VPN_HOST} failed (Pi-hole down or no cutover)"
  warned=1
fi

# --- VPN HTTPS (optional if tunnel not up) ---
vpn_reachable=0
if ping -c 1 -W 2 "$WG_VPN_IP" &>/dev/null || ping -c 1 -t 2 "$WG_VPN_IP" &>/dev/null; then
  vpn_reachable=1
fi

if [[ "$SKIP_VPN_HTTPS" == "1" ]]; then
  log "SKIP: VPN HTTPS (SKIP_VPN_HTTPS=1)"
elif [[ "$vpn_reachable" -eq 0 ]]; then
  log "WARN: ${WG_VPN_IP} unreachable — enable WireGuard client tunnel, then re-run"
  warned=1
else
  log "OK: ping ${WG_VPN_IP} (tunnel up)"
  https_code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 \
    "https://${HA_VPN_HOST}/" || true)"
  if [[ "$https_code" =~ ^[23] || "$https_code" == "401" || "$https_code" == "400" ]]; then
    log "OK: https://${HA_VPN_HOST}/ → HTTP ${https_code}"
  else
    log "FAIL: https://${HA_VPN_HOST}/ → HTTP ${https_code:-000}"
    log "  Check: Caddy journal, CF_API_TOKEN, LE DNS-01, HA trusted_proxies=${WG_LAN_IP}"
    failed=1
  fi
fi

echo ""
if [[ "$failed" -eq 0 ]]; then
  log "=== Critical checks passed${warned:+ (with warnings)} ==="
  cat <<EOF
Go / no-go (docs/wireguard.md):
  1. Without VPN: https://${HA_VPN_HOST} must fail
  2. With VPN (mobile data): valid LE cert + HA UI
  3. LAN: ${HA_LAN_URL} still OK for Satellite1
  4. Host RAM: free -h on Proxmox; if <500 MiB free → qm set 101 --memory 512
EOF
  exit 0
fi

log "=== Some critical checks failed — see docs/wireguard.md ==="
exit 1
