#!/usr/bin/env bash
# ==============================================================================
# fix_proxmox_cluster.sh — permanent fix for "pve-cluster dead after reboot"
#
# Root cause: cloud-init rewrites /etc/hosts at every boot (waynelab-core ->
# 127.0.1.1), so pmxcfs refuses to start, /etc/pve never mounts and pve-guests
# cannot autostart any VM (HAOS, Pi-hole, WireGuard).
#
# The setting that wins is `manage_etc_hosts: true` in /boot/firmware/user-data
# (NoCloud seed): it overrides /etc/cloud/cloud.cfg and cloud.cfg.d/*. Editing
# only cloud.cfg (the old fix) does NOT survive a reboot.
#
# This script (idempotent):
#   1. sets manage_etc_hosts: false in user-data, cloud.cfg and cloud.cfg.d
#   2. installs the /etc/hosts guard + pve-cluster systemd drop-in (self-heal)
#   3. repairs /etc/hosts now and restarts Proxmox services + onboot VMs
#
# Usage (needs the whole directory, it installs ensure_hosts.sh and the drop-in):
#   scp -r infrastructure/nodes/core pi@192.168.1.100:/tmp/waynelab-core
#   ssh -t pi@192.168.1.100 "sudo bash /tmp/waynelab-core/fix_proxmox_cluster.sh"
#
# Options: --no-restart  only persist config (used by setup_host.sh, before PVE exists)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_USER_DATA="${SEED_USER_DATA:-/boot/firmware/user-data}"
BACKUP_DIR="/var/backups/waynelab"
GUARD_BIN="/usr/local/sbin/waynelab-ensure-hosts"
DROPIN_DIR="/etc/systemd/system/pve-cluster.service.d"
VM_WAIT_SECS="${VM_WAIT_SECS:-180}"
RESTART=1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

check_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "Run as root: sudo bash $0"
        exit 1
    fi
}

backup_once() {
    local src="$1" dest
    dest="${BACKUP_DIR}/$(basename "${src}").orig"
    mkdir -p "${BACKUP_DIR}"
    [[ -f "${dest}" ]] || cp -p "${src}" "${dest}"
}

set_manage_etc_hosts_false() {
    local file="$1"
    [[ -f "${file}" ]] || return 0
    backup_once "${file}"
    if grep -q '^manage_etc_hosts:' "${file}"; then
        sed -i 's/^manage_etc_hosts:.*/manage_etc_hosts: false/' "${file}"
    else
        printf '\nmanage_etc_hosts: false\n' >> "${file}"
    fi
    log "manage_etc_hosts: false -> ${file}"
}

disable_cloud_init_hosts() {
    # user-data is the one that actually wins; the others are belt and braces.
    set_manage_etc_hosts_false "${SEED_USER_DATA}"
    set_manage_etc_hosts_false /etc/cloud/cloud.cfg
    mkdir -p /etc/cloud/cloud.cfg.d
    cat > /etc/cloud/cloud.cfg.d/99-waynelab-hosts.cfg <<'EOF'
# Keep Proxmox pmxcfs resolvable after reboot (hostname must not map to 127.0.1.1).
# NOTE: /boot/firmware/user-data overrides this file; it must also say false.
manage_etc_hosts: false
EOF
}

install_guard() {
    install -m 0755 "${SCRIPT_DIR}/ensure_hosts.sh" "${GUARD_BIN}"
    mkdir -p "${DROPIN_DIR}"
    install -m 0644 "${SCRIPT_DIR}/systemd/pve-cluster-waynelab.conf" "${DROPIN_DIR}/waynelab.conf"
    systemctl daemon-reload
    log "Installed ${GUARD_BIN} and ${DROPIN_DIR}/waynelab.conf"
}

restart_proxmox() {
    "${GUARD_BIN}"
    systemctl reset-failed pve-cluster pvestatd pvedaemon pveproxy pve-guests 2>/dev/null || true
    log "Restarting Proxmox services..."
    systemctl restart pve-cluster
    sleep 2
    systemctl restart pvestatd pvedaemon pveproxy
    # pve-guests refuses manual start/stop (dependency-only unit), so trigger the same
    # onboot=1 + startup-order logic (Pi-hole=1, WireGuard=2) through the API instead.
    log "Starting onboot VMs (startall)..."
    pvesh create "/nodes/$(hostname)/startall" >/dev/null \
        || log "startall failed; falling back to wait_for_haos"
}

wait_for_haos() {
    local waited=0
    log "Waiting for HAOS VM (100) to run (max ${VM_WAIT_SECS}s)..."
    until qm status 100 2>/dev/null | grep -q running; do
        if (( waited >= VM_WAIT_SECS )); then
            log "pve-guests did not start VM 100; starting it manually"
            qm start 100
            break
        fi
        sleep 5
        waited=$((waited + 5))
    done
}

verify() {
    log "Verification:"
    getent hosts "$(hostname)"
    grep -E '^manage_etc_hosts:' "${SEED_USER_DATA}" /etc/cloud/cloud.cfg 2>/dev/null || true
    systemctl is-active pve-cluster pvestatd pvedaemon pveproxy
    qm list
}

main() {
    local arg
    for arg in "$@"; do
        [[ "${arg}" == "--no-restart" ]] && RESTART=0
    done
    check_root
    disable_cloud_init_hosts
    install_guard
    if (( RESTART )); then
        restart_proxmox
        wait_for_haos
        verify
    fi
}

main "$@"
