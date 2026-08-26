#!/usr/bin/env bash
# ==============================================================================
# create_haos_vm.sh — Provision a Home Assistant OS VM on Proxmox VE (RPi 5)
#
# Usage:
#   bash create_haos_vm.sh [--vmid <id>] [--storage <storage>] [--recreate]
#
# Prerequisites:
#   - Proxmox VE installed and running on RPi 5 (ARM64)
#   - Root access to Proxmox host
#   - Internet access to download HAOS image
# ==============================================================================
set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration (override via environment variables)
# ------------------------------------------------------------------------------
VMID="${VMID:-100}"
VM_NAME="${VM_NAME:-haos}"
STORAGE="${STORAGE:-local}"
CORES="${CORES:-2}"
MEMORY="${MEMORY:-2048}"
DISK_SIZE="${DISK_SIZE:-64G}"
BRIDGE="${BRIDGE:-vmbr0}"
HAOS_VERSION="${HAOS_VERSION:-13.2}"
HAOS_IMAGE="haos_generic-aarch64-${HAOS_VERSION}.qcow2"
HAOS_URL="https://github.com/home-assistant/operating-system/releases/download/${HAOS_VERSION}/${HAOS_IMAGE}.xz"
DOWNLOAD_DIR="/var/lib/vz/template/iso"
RECREATE=0

# ------------------------------------------------------------------------------
# Parse arguments
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vmid)     VMID="$2";      shift 2 ;;
        --storage)  STORAGE="$2";   shift 2 ;;
        --recreate) RECREATE=1;     shift ;;
        *)          echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

remove_existing_vm() {
    if ! qm status "$VMID" &>/dev/null; then
        return
    fi

    log "Stopping and removing existing VM ${VMID}..."
    qm stop "$VMID" --timeout 120 2>/dev/null || true
    qm destroy "$VMID" --destroy-unreferenced-disks 1
}

check_proxmox_daemons() {
    local failed=0
    for svc in pve-cluster pvestatd; do
        if ! systemctl is-active --quiet "$svc"; then
            log "ERROR: ${svc} is not active."
            failed=1
        fi
    done
    if [[ "$failed" -eq 1 ]]; then
        local resolved
        resolved="$(getent hosts "$(hostname -s)" | awk '{print $1}' || true)"
        log "Proxmox cluster IPC failed (often hostname -> 127.0.1.1 in /etc/hosts)."
        log "Fix: sudo bash infrastructure/nodes/core/fix_proxmox_cluster.sh"
        log "Current resolution for $(hostname -s): ${resolved:-unknown}"
        exit 1
    fi
}

check_prerequisites() {
    if ! command -v qm &>/dev/null; then
        log "ERROR: 'qm' not found. This script must run on a Proxmox VE host."
        exit 1
    fi

    check_proxmox_daemons

    if qm status "$VMID" &>/dev/null; then
        if [[ "$RECREATE" -eq 1 ]]; then
            remove_existing_vm
        else
            log "ERROR: VM ${VMID} already exists. Use --recreate or a different VMID."
            exit 1
        fi
    fi
}

download_haos_image() {
    local image_path="${DOWNLOAD_DIR}/${HAOS_IMAGE}"

    if [[ -f "$image_path" ]]; then
        log "HAOS image already exists at ${image_path}, skipping download."
        return
    fi

    log "Downloading HAOS ${HAOS_VERSION} (${HAOS_IMAGE})..."
    mkdir -p "$DOWNLOAD_DIR"
    wget -q --show-progress -O "${image_path}.xz" "$HAOS_URL"

    log "Extracting image..."
    xz -d "${image_path}.xz"

    log "Image ready at ${image_path}"
}

create_vm() {
    local image_path="${DOWNLOAD_DIR}/${HAOS_IMAGE}"
    local scsi_disk="${STORAGE}:${VMID}/vm-${VMID}-disk-1.raw"

    log "Creating VM ${VMID} (${VM_NAME})..."

    qm create "$VMID" \
        --name "$VM_NAME" \
        --ostype l26 \
        --machine virt \
        --cores "$CORES" \
        --memory "$MEMORY" \
        --net0 "virtio,bridge=${BRIDGE}" \
        --bios ovmf \
        --agent enabled=1 \
        --onboot 1

    qm set "$VMID" --efidisk0 "${STORAGE}:1,format=raw,efitype=4m,pre-enrolled-keys=0"

    log "Importing HAOS disk image to ${STORAGE}..."
    qm importdisk "$VMID" "$image_path" "$STORAGE" --format raw

    log "Attaching disk and resizing to ${DISK_SIZE}..."
    qm set "$VMID" \
        --scsihw virtio-scsi-pci \
        --scsi0 "$scsi_disk" \
        --boot order=scsi0 \
        --serial0 socket

    qm resize "$VMID" scsi0 "$DISK_SIZE"

    log "VM ${VMID} created successfully (disk: ${DISK_SIZE})."
}

start_vm() {
    log "Starting VM ${VMID}..."
    qm start "$VMID"
    log "VM ${VMID} is now running."
    log "Access Home Assistant at http://<vm-ip>:8123 (allow 5-10 minutes for first boot)."
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log "=== HAOS VM Provisioning (ARM64) ==="
    log "VMID: ${VMID} | Name: ${VM_NAME} | Cores: ${CORES} | RAM: ${MEMORY}MB"
    log "Storage: ${STORAGE} | Disk: ${DISK_SIZE} | Bridge: ${BRIDGE} | HAOS: ${HAOS_VERSION}"
    echo ""

    check_prerequisites
    download_haos_image
    create_vm
    start_vm

    log "=== Provisioning complete ==="
}

main "$@"
