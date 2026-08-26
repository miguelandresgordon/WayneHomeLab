#!/usr/bin/env bash
# ==============================================================================
# create_peer.sh — Add a WireGuard peer and emit client config + QR
#
# Usage (on WireGuard VM, as root):
#   bash create_peer.sh <peer-name> [peer-ip-last-octet]
# Example:
#   bash create_peer.sh macbook 10
#   bash create_peer.sh iphone
#
# Client DNS = Pi-hole (split-horizon for ha.waynehomelab.com → 10.44.0.1).
# AllowedIPs = LAN + VPN subnet (split tunnel; not full tunnel).
# ==============================================================================
set -euo pipefail

WG_IFACE="${WG_IFACE:-wg0}"
WG_DIR="/etc/wireguard"
WG_CONFIG="${WG_DIR}/${WG_IFACE}.conf"
WG_SUBNET_PREFIX="${WG_SUBNET_PREFIX:-10.44.0}"
WG_PORT="${WG_PORT:-51820}"
WG_ENDPOINT="${WG_ENDPOINT:-vpn.waynehomelab.com}"
LAN_CIDR="${LAN_CIDR:-192.168.1.0/24}"
PIHOLE_DNS="${PIHOLE_DNS:-192.168.1.53}"
PEERS_DIR="${WG_DIR}/peers"

PEER_NAME="${1:-}"
PEER_OCTET="${2:-}"

usage() {
  echo "Usage: bash create_peer.sh <peer-name> [peer-ip-last-octet]"
}

require_root() {
  if [[ ${EUID} -ne 0 ]]; then
    echo "ERROR: run as root (sudo)"
    exit 1
  fi
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: Missing command '$1'"
    exit 1
  }
}

next_octet() {
  local max=9
  if [[ -f "${PEERS_DIR}/.next_octet" ]]; then
    max="$(cat "${PEERS_DIR}/.next_octet")"
  fi
  max=$((max + 1))
  if [[ "$max" -ge 254 ]]; then
    echo "ERROR: no free peer octets left in ${WG_SUBNET_PREFIX}.0/24"
    exit 1
  fi
  echo "${max}" > "${PEERS_DIR}/.next_octet"
  echo "${max}"
}

main() {
  [[ -n "${PEER_NAME}" ]] || { usage; exit 1; }
  require_root
  require_cmd wg
  require_cmd qrencode

  [[ -f "${WG_CONFIG}" ]] || {
    echo "ERROR: ${WG_CONFIG} missing. Run install_wireguard.sh first."
    exit 1
  }
  [[ -f "${WG_DIR}/server_public.key" ]] || {
    echo "ERROR: ${WG_DIR}/server_public.key missing."
    exit 1
  }

  mkdir -p "${PEERS_DIR}"
  chmod 700 "${PEERS_DIR}"

  if [[ -f "${PEERS_DIR}/${PEER_NAME}.conf" ]]; then
    echo "ERROR: peer '${PEER_NAME}' already exists (${PEERS_DIR}/${PEER_NAME}.conf)"
    exit 1
  fi

  if [[ -z "${PEER_OCTET}" ]]; then
    PEER_OCTET="$(next_octet)"
  fi

  local peer_ip="${WG_SUBNET_PREFIX}.${PEER_OCTET}/32"
  local priv_file="${PEERS_DIR}/${PEER_NAME}_private.key"
  local pub_file="${PEERS_DIR}/${PEER_NAME}_public.key"
  local psk_file="${PEERS_DIR}/${PEER_NAME}_psk.key"
  local conf_file="${PEERS_DIR}/${PEER_NAME}.conf"

  umask 077
  wg genkey | tee "${priv_file}" | wg pubkey > "${pub_file}"
  wg genpsk > "${psk_file}"

  local server_pub peer_pub psk peer_priv
  server_pub="$(cat "${WG_DIR}/server_public.key")"
  peer_pub="$(cat "${pub_file}")"
  psk="$(cat "${psk_file}")"
  peer_priv="$(cat "${priv_file}")"

  cat >> "${WG_CONFIG}" <<EOF

[Peer]
# ${PEER_NAME}
PublicKey = ${peer_pub}
PresharedKey = ${psk}
AllowedIPs = ${peer_ip}
EOF

  cat > "${conf_file}" <<EOF
[Interface]
PrivateKey = ${peer_priv}
Address = ${peer_ip}
DNS = ${PIHOLE_DNS}

[Peer]
PublicKey = ${server_pub}
PresharedKey = ${psk}
Endpoint = ${WG_ENDPOINT}:${WG_PORT}
AllowedIPs = ${LAN_CIDR}, ${WG_SUBNET_PREFIX}.0/24
PersistentKeepalive = 25
EOF

  chmod 600 "${conf_file}" "${priv_file}" "${psk_file}"
  systemctl restart "wg-quick@${WG_IFACE}"

  echo "Peer created: ${PEER_NAME}"
  echo "VPN IP: ${peer_ip}"
  echo "Config path: ${conf_file}"
  echo "Copy off-box (do not commit): scp pi@192.168.1.55:${conf_file} ."
  echo ""
  echo "QR (for mobile import):"
  qrencode -t ansiutf8 < "${conf_file}"
}

main "$@"
