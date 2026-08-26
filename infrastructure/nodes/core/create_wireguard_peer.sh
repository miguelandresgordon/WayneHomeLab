#!/usr/bin/env bash
# ==============================================================================
# create_wireguard_peer.sh
#
# Create a new WireGuard peer on server and emit client configuration.
#
# Usage:
#   bash create_wireguard_peer.sh <peer-name> [peer-ip-last-octet]
# Example:
#   bash create_wireguard_peer.sh macbook 10
# ==============================================================================
set -euo pipefail

WG_IFACE="${WG_IFACE:-wg0}"
WG_DIR="/etc/wireguard"
WG_CONFIG="${WG_DIR}/${WG_IFACE}.conf"
WG_SUBNET_PREFIX="${WG_SUBNET_PREFIX:-10.44.0}"
WG_PORT="${WG_PORT:-51820}"
WG_ENDPOINT="${WG_ENDPOINT:-vpn.waynehomelab.com}"
LAN_CIDR="${LAN_CIDR:-192.168.1.0/24}"
PEERS_DIR="${WG_DIR}/peers"

PEER_NAME="${1:-}"
PEER_OCTET="${2:-}"

usage() {
  echo "Usage: bash create_wireguard_peer.sh <peer-name> [peer-ip-last-octet]"
}

require_root() {
  if [[ ${EUID} -ne 0 ]]; then
    echo "ERROR: run as root"
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
  echo "${max}" > "${PEERS_DIR}/.next_octet"
  echo "${max}"
}

main() {
  [[ -n "${PEER_NAME}" ]] || { usage; exit 1; }
  require_root
  require_cmd wg
  require_cmd qrencode
  mkdir -p "${PEERS_DIR}"
  chmod 700 "${PEERS_DIR}"

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

  local server_pub
  server_pub="$(cat "${WG_DIR}/server_public.key")"
  local peer_pub
  peer_pub="$(cat "${pub_file}")"
  local psk
  psk="$(cat "${psk_file}")"
  local peer_priv
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
DNS = 1.1.1.1

[Peer]
PublicKey = ${server_pub}
PresharedKey = ${psk}
Endpoint = ${WG_ENDPOINT}:${WG_PORT}
AllowedIPs = ${LAN_CIDR}, ${WG_SUBNET_PREFIX}.0/24
PersistentKeepalive = 25
EOF

  chmod 600 "${conf_file}"
  systemctl restart "wg-quick@${WG_IFACE}"

  echo "Peer created: ${PEER_NAME}"
  echo "Config path: ${conf_file}"
  echo ""
  echo "QR (for mobile import):"
  qrencode -t ansiutf8 < "${conf_file}"
}

main "$@"
