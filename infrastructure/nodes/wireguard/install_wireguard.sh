#!/usr/bin/env bash
# ==============================================================================
# install_wireguard.sh — WireGuard server on the dedicated Debian VM (VMID 102)
#
# Run on the guest (192.168.1.55), as root:
#   WG_ENDPOINT=vpn.waynehomelab.com bash install_wireguard.sh
#
# Does NOT install WireGuard on the Proxmox host.
# After install: create_peer.sh for each client.
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

detect_uplink_iface() {
  ip route show default | awk '/default/ {print $5; exit}'
}

install_packages() {
  log "Installing WireGuard packages..."
  apt-get update -qq
  apt-get install -y -qq wireguard wireguard-tools qrencode iptables
}

generate_server_keys() {
  mkdir -p "${WG_DIR}/peers"
  chmod 700 "${WG_DIR}"
  chmod 700 "${WG_DIR}/peers"

  if [[ ! -f "${SERVER_PRIV_KEY_FILE}" ]]; then
    log "Generating server keypair..."
    umask 077
    wg genkey | tee "${SERVER_PRIV_KEY_FILE}" | wg pubkey > "${SERVER_PUB_KEY_FILE}"
    chmod 600 "${SERVER_PRIV_KEY_FILE}" "${SERVER_PUB_KEY_FILE}"
  else
    log "Server keys already exist, keeping them."
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

  # SaveConfig=false: peers are appended by create_peer.sh; do not let wg-quick rewrite.
  # Preserve existing [Peer] sections if config already exists.
  if [[ -f "${CONFIG_FILE}" ]] && grep -q '^\[Peer\]' "${CONFIG_FILE}"; then
    log "Existing peers found — rewriting [Interface] only via temp merge."
    local peers_block
    peers_block="$(awk '/^\[Peer\]/{p=1} p' "${CONFIG_FILE}")"
    cat > "${CONFIG_FILE}" <<EOF
[Interface]
Address = ${WG_SERVER_IP}
ListenPort = ${WG_PORT}
PrivateKey = ${server_priv}
SaveConfig = false

# NAT traffic from VPN clients to LAN
PostUp = iptables -A FORWARD -i ${WG_IFACE} -j ACCEPT; iptables -A FORWARD -o ${WG_IFACE} -j ACCEPT; iptables -t nat -A POSTROUTING -o ${uplink_iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i ${WG_IFACE} -j ACCEPT; iptables -D FORWARD -o ${WG_IFACE} -j ACCEPT; iptables -t nat -D POSTROUTING -o ${uplink_iface} -j MASQUERADE

${peers_block}
EOF
  else
    cat > "${CONFIG_FILE}" <<EOF
[Interface]
Address = ${WG_SERVER_IP}
ListenPort = ${WG_PORT}
PrivateKey = ${server_priv}
SaveConfig = false

# NAT traffic from VPN clients to LAN
PostUp = iptables -A FORWARD -i ${WG_IFACE} -j ACCEPT; iptables -A FORWARD -o ${WG_IFACE} -j ACCEPT; iptables -t nat -A POSTROUTING -o ${uplink_iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i ${WG_IFACE} -j ACCEPT; iptables -D FORWARD -o ${WG_IFACE} -j ACCEPT; iptables -t nat -D POSTROUTING -o ${uplink_iface} -j MASQUERADE
EOF
  fi

  chmod 600 "${CONFIG_FILE}"
  log "Wrote ${CONFIG_FILE} (uplink=${uplink_iface})"
}

enable_forwarding() {
  cat > /etc/sysctl.d/99-wireguard-forward.conf <<'EOF'
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
EOF
  sysctl --system >/dev/null
  log "IP forwarding enabled."
}

enable_service() {
  systemctl enable "wg-quick@${WG_IFACE}"
  systemctl restart "wg-quick@${WG_IFACE}"
  log "Service wg-quick@${WG_IFACE} active."
}

print_summary() {
  log "WireGuard ready on this VM."
  log "Endpoint: ${WG_ENDPOINT}:${WG_PORT}"
  log "Server VPN IP: ${WG_SERVER_IP}"
  log "Server public key: $(cat "${SERVER_PUB_KEY_FILE}")"
  log "LAN routes for peers: ${LAN_CIDR}, ${WG_SUBNET}"
  log "Next: bash create_peer.sh <name>  (DNS will be Pi-hole 192.168.1.53)"
  log "Router: DNAT UDP ${WG_PORT} → this VM LAN IP (192.168.1.55)."
}

main() {
  require_root
  require_cmd ip
  install_packages
  require_cmd wg
  generate_server_keys
  write_config
  enable_forwarding
  enable_service
  print_summary
}

main "$@"
