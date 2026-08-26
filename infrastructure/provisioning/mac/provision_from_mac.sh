#!/usr/bin/env bash
# ==============================================================================
# provision_from_mac.sh
#
# Run remote provisioning steps for Pi5 and Pi3 from a macOS workstation.
#
# This script does not flash media; it assumes both devices are reachable by SSH.
# ==============================================================================
set -euo pipefail

PI5_IP="${PI5_IP:-192.168.1.100}"
PI3_IP="${PI3_IP:-192.168.1.101}"
PI5_USER="${PI5_USER:-pi}"
PI3_USER="${PI3_USER:-dietpi}"
ENABLE_EDGE_SETUP="${ENABLE_EDGE_SETUP:-true}"
ENABLE_WIREGUARD="${ENABLE_WIREGUARD:-true}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

copy_and_run_pi5_host_setup() {
  log "Copying Pi5 host setup scripts..."
  scp "${ROOT_DIR}/infrastructure/nodes/core/setup_host.sh" "${PI5_USER}@${PI5_IP}:/tmp/"
  scp "${ROOT_DIR}/infrastructure/nodes/core/sysctl.conf" "${PI5_USER}@${PI5_IP}:/tmp/"
  ssh "${PI5_USER}@${PI5_IP}" "sudo bash /tmp/setup_host.sh"
}

copy_and_run_edge_setup() {
  if [[ "${ENABLE_EDGE_SETUP}" != "true" ]]; then
    log "Skipping edge setup (ENABLE_EDGE_SETUP=${ENABLE_EDGE_SETUP})"
    return
  fi

  log "Copying and executing Pi3 edge setup..."
  scp "${ROOT_DIR}/infrastructure/nodes/edge/setup_edge.sh" "${PI3_USER}@${PI3_IP}:/tmp/"
  ssh "${PI3_USER}@${PI3_IP}" "sudo SSD_DEVICE=/dev/sda1 bash /tmp/setup_edge.sh"
}

install_wireguard() {
  if [[ "${ENABLE_WIREGUARD}" != "true" ]]; then
    log "Skipping WireGuard setup (ENABLE_WIREGUARD=${ENABLE_WIREGUARD})"
    return
  fi

  log "Installing WireGuard on Pi5..."
  scp "${ROOT_DIR}/infrastructure/nodes/core/install_wireguard.sh" "root@${PI5_IP}:/tmp/"
  ssh "root@${PI5_IP}" "WG_ENDPOINT=vpn.waynehomelab.com bash /tmp/install_wireguard.sh"

  log "Creating initial peers..."
  scp "${ROOT_DIR}/infrastructure/nodes/core/create_wireguard_peer.sh" "root@${PI5_IP}:/tmp/"
  ssh "root@${PI5_IP}" "bash /tmp/create_wireguard_peer.sh macbook"
  ssh "root@${PI5_IP}" "bash /tmp/create_wireguard_peer.sh iphone"
}

main() {
  log "=== Provision from macOS ==="
  copy_and_run_pi5_host_setup
  copy_and_run_edge_setup
  install_wireguard
  log "Provisioning stage complete."
}

main "$@"
