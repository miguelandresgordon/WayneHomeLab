#!/usr/bin/env bash
# ==============================================================================
# setup_backup_sink.sh
#
# Configure Raspberry Pi 3 (DietPi) as a backup sink for HA/Proxmox artifacts.
#
# Usage:
#   sudo bash setup_backup_sink.sh
# Optional env:
#   BACKUP_MOUNT=/mnt/ssd
#   BACKUP_USER=backup
# ==============================================================================
set -euo pipefail

BACKUP_MOUNT="${BACKUP_MOUNT:-/mnt/ssd}"
BACKUP_ROOT="${BACKUP_MOUNT}/backups"
BACKUP_USER="${BACKUP_USER:-backup}"
LOG_FILE="/var/log/setup_backup_sink.log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

require_root() {
  if [[ ${EUID} -ne 0 ]]; then
    echo "ERROR: run as root"
    exit 1
  fi
}

install_packages() {
  log "Installing backup dependencies..."
  apt-get update -qq
  apt-get install -y -qq rsync openssh-server
}

ensure_backup_user() {
  if ! id "${BACKUP_USER}" >/dev/null 2>&1; then
    log "Creating user ${BACKUP_USER}..."
    useradd -m -s /bin/bash "${BACKUP_USER}"
  fi
}

create_backup_dirs() {
  log "Creating backup directory structure under ${BACKUP_ROOT}..."
  mkdir -p "${BACKUP_ROOT}/home-assistant"
  mkdir -p "${BACKUP_ROOT}/proxmox"
  mkdir -p "${BACKUP_ROOT}/wireguard"
  chown -R "${BACKUP_USER}:${BACKUP_USER}" "${BACKUP_ROOT}"
  chmod -R 750 "${BACKUP_ROOT}"
}

configure_ssh_for_backup_user() {
  local ssh_dir="/home/${BACKUP_USER}/.ssh"
  mkdir -p "${ssh_dir}"
  chmod 700 "${ssh_dir}"
  touch "${ssh_dir}/authorized_keys"
  chmod 600 "${ssh_dir}/authorized_keys"
  chown -R "${BACKUP_USER}:${BACKUP_USER}" "${ssh_dir}"
}

print_summary() {
  log "Backup sink ready."
  log "Backup user: ${BACKUP_USER}"
  log "Backup root: ${BACKUP_ROOT}"
  log "Next: add public SSH keys to /home/${BACKUP_USER}/.ssh/authorized_keys"
}

main() {
  require_root
  install_packages
  ensure_backup_user
  create_backup_dirs
  configure_ssh_for_backup_user
  print_summary
}

main "$@"
