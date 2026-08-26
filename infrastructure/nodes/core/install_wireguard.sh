#!/usr/bin/env bash
# ==============================================================================
# install_wireguard.sh
#
# Install and configure WireGuard server on the RPi5 host.
#
# Usage:
#   WG_ENDPOINT=vpn.waynehomelab.com WG_PORT=51820 bash install_wireguard.sh
# ==============================================================================
set -euo pipefail

WG_IFACE="${WG_IFACE:-wg0}"
WG_PORT="${WG_PORT:-51820}"
WG_SUBNET="${WG_SUBNET:-10.44.0.0/24}"
WG_SERVER_IP="${WG_SERVER_IP:-10.44.0.1/24}"
WG_ENDPOINT="${WG_ENDPOINT:-vpn.waynehomelab.com}"
LAN_CIDR="${LAN_CIDR:-192.168.1.0/24}"

WG_DIR="/etc/wireguard"
SERVER_PRIV_KEY_FILE="${WG_DIR}/server_private.key"
SERVER_PUB_KEY_FILE="${WG_DIR}/server_public.key"
CONFIG_FILE="${WG_DIR}/${WG_IFACE}.conf"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
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

detect_uplink_iface() {
  ip route show default | awk '/default/ {print $5; exit}'
}

install_packages() {
  log "Installing WireGuard packages..."
  apt-get update -qq
  apt-get install -y -qq wireguard wireguard-tools qrencode
}

generate_server_keys() {
  mkdir -p "${WG_DIR}/peers"
  chmod 700 "${WG_DIR}"

  if [[ ! -f "${SERVER_PRIV_KEY_FILE}" ]]; then
    log "Generating server keypair..."
    umask 077
    wg genkey | tee "${SERVER_PRIV_KEY_FILE}" | wg pubkey > "${SERVER_PUB_KEY_FILE}"
  fi
}

write_config() {
  local uplink_iface
  uplink_iface="$(detect_uplink_iface)"

  if [[ -z "${uplink_iface}" ]]; then
    echo "ERROR: Could not detect uplink interface"
    exit 1
  fi

  local server_priv
  server_priv="$(cat "${SERVER_PRIV_KEY_FILE}")"

  cat > "${CONFIG_FILE}" <<EOF
[Interface]
Address = ${WG_SERVER_IP}
ListenPort = ${WG_PORT}
PrivateKey = ${server_priv}
SaveConfig = true

# NAT traffic from VPN clients to LAN and internet
PostUp = iptables -A FORWARD -i ${WG_IFACE} -j ACCEPT; iptables -A FORWARD -o ${WG_IFACE} -j ACCEPT; iptables -t nat -A POSTROUTING -o ${uplink_iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i ${WG_IFACE} -j ACCEPT; iptables -D FORWARD -o ${WG_IFACE} -j ACCEPT; iptables -t nat -D POSTROUTING -o ${uplink_iface} -j MASQUERADE
EOF

  chmod 600 "${CONFIG_FILE}"
}

enable_forwarding() {
  cat > /etc/sysctl.d/99-wireguard-forward.conf <<'EOF'
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
EOF
  sysctl --system >/dev/null
}

enable_service() {
  systemctl enable "wg-quick@${WG_IFACE}"
  systemctl restart "wg-quick@${WG_IFACE}"
}

print_summary() {
  log "WireGuard ready."
  log "Endpoint: ${WG_ENDPOINT}:${WG_PORT}"
  log "Server public key: $(cat "${SERVER_PUB_KEY_FILE}")"
  log "LAN routes for peers: ${LAN_CIDR}"
  log "Next: run create_wireguard_peer.sh for each client."
}

main() {
  require_root
  require_cmd ip
  install_packages
  generate_server_keys
  write_config
  enable_forwarding
  enable_service
  print_summary
}

main "$@"
