#!/usr/bin/env bash
# ==============================================================================
# create_wireguard_vm.sh — Provision a Debian 12 ARM64 cloud-init VM for
#                          WireGuard + Caddy on Proxmox VE / PXVIRT (RPi 5)
#
# Usage (on Proxmox host, as root or via sudo):
#   bash create_wireguard_vm.sh [--vmid <id>] [--storage <storage>] [--recreate]
#
# Environment overrides:
#   VMID, VM_NAME, STORAGE, CORES, MEMORY, BALLOON, DISK_SIZE, BRIDGE
#   VM_IP (CIDR), GATEWAY, NAMESERVER, CI_USER, SSH_PUBLIC_KEY / SSH_KEY_FILE
#   STARTUP_ORDER, DEBIAN_IMAGE_URL
#
# Defaults match WayneHomelab plan:
#   VMID 102 · IP 192.168.1.55/24 · 1 vCPU · 512 MiB · balloon 128 · disk 4G
#   storage=local · bridge=vmbr0 · cloud-init on SCSI (ARM64, no IDE)
#   startup order=2 (after Pi-hole order=1)
#
# After the VM boots:
#   infrastructure/nodes/wireguard/install_wireguard.sh
#   infrastructure/nodes/wireguard/install_caddy.sh
# ==============================================================================
set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
VMID="${VMID:-102}"
VM_NAME="${VM_NAME:-wireguard}"
STORAGE="${STORAGE:-local}"
CORES="${CORES:-1}"
MEMORY="${MEMORY:-512}"
BALLOON="${BALLOON:-128}"
DISK_SIZE="${DISK_SIZE:-4G}"
BRIDGE="${BRIDGE:-vmbr0}"
VM_IP="${VM_IP:-192.168.1.55/24}"
GATEWAY="${GATEWAY:-192.168.1.1}"
NAMESERVER="${NAMESERVER:-1.1.1.1}"
CI_USER="${CI_USER:-pi}"
STARTUP_ORDER="${STARTUP_ORDER:-2}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-/var/lib/vz/template/iso}"
DEBIAN_IMAGE="${DEBIAN_IMAGE:-debian-12-generic-arm64.qcow2}"
DEBIAN_IMAGE_URL="${DEBIAN_IMAGE_URL:-https://cloud.debian.org/images/cloud/bookworm/latest/${DEBIAN_IMAGE}}"
SSH_PUBLIC_KEY="${SSH_PUBLIC_KEY:-}"
SSH_KEY_FILE="${SSH_KEY_FILE:-}"
RECREATE=0

# ------------------------------------------------------------------------------
# Parse arguments
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vmid)     VMID="$2";      shift 2 ;;
        --storage)  STORAGE="$2";   shift 2 ;;
        --recreate) RECREATE=1;     shift ;;
        --help|-h)
            sed -n '2,28p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

die() {
    log "ERROR: $*"
    exit 1
}

resolve_ssh_key() {
    if [[ -n "$SSH_PUBLIC_KEY" ]]; then
        return
    fi
    if [[ -n "$SSH_KEY_FILE" ]]; then
        [[ -f "$SSH_KEY_FILE" ]] || die "SSH_KEY_FILE not found: ${SSH_KEY_FILE}"
        SSH_PUBLIC_KEY="$(grep -E '^(ssh-|ecdsa-)' "$SSH_KEY_FILE" | head -n1 || true)"
        [[ -n "$SSH_PUBLIC_KEY" ]] || die "No public key line in ${SSH_KEY_FILE}"
        return
    fi

    # Prefer the invoking user's keys when run via sudo (avoid injecting root@host).
    local real_home candidate
    real_home="${HOME:-}"
    if [[ -n "${SUDO_USER:-}" ]]; then
        real_home="$(getent passwd "$SUDO_USER" | awk -F: '{print $6}')"
    fi

    for candidate in \
        "/home/pi/.ssh/authorized_keys" \
        "${real_home}/.ssh/authorized_keys" \
        "${real_home}/.ssh/id_ed25519.pub" \
        "${real_home}/.ssh/id_rsa.pub" \
        "${HOME}/.ssh/id_ed25519.pub" \
        "${HOME}/.ssh/id_rsa.pub"
    do
        if [[ -f "$candidate" ]]; then
            SSH_PUBLIC_KEY="$(grep -E '^ssh-ed25519 ' "$candidate" | head -n1 || true)"
            if [[ -z "$SSH_PUBLIC_KEY" ]]; then
                SSH_PUBLIC_KEY="$(grep -E '^(ssh-|ecdsa-)' "$candidate" | head -n1 || true)"
            fi
            if [[ -n "$SSH_PUBLIC_KEY" ]]; then
                log "Using SSH public key from ${candidate}"
                return
            fi
        fi
    done
    die "No SSH public key found. Set SSH_PUBLIC_KEY or SSH_KEY_FILE=/path/to/id_ed25519.pub"
}

remove_existing_vm() {
    if ! qm status "$VMID" &>/dev/null; then
        return
    fi

    log "Stopping and removing existing VM ${VMID}..."
    qm stop "$VMID" --timeout 120 2>/dev/null || true
    qm destroy "$VMID" --destroy-unreferenced-disks 1 --purge 1
}

check_proxmox_daemons() {
    local failed=0
    local svc
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

check_host_ram() {
    local mem_total_kib mem_avail_kib mem_avail_mib
    mem_total_kib="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
    mem_avail_kib="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
    mem_avail_mib=$((mem_avail_kib / 1024))

    log "Host RAM: total=$((mem_total_kib / 1024)) MiB, available=${mem_avail_mib} MiB"
    log "This VM will request ${MEMORY} MiB (balloon min ${BALLOON})."
    log "Target: leave ~1 GB free for Proxmox host after all VMs."

    if [[ "$mem_avail_mib" -lt $((MEMORY + 256)) ]]; then
        log "WARN: host available RAM (${mem_avail_mib} MiB) looks tight for +${MEMORY} MiB."
        log "If host stays <500 MiB free after boot, lower Pi-hole: qm set 101 --memory 512"
    fi
}

check_prerequisites() {
    if ! command -v qm &>/dev/null; then
        die "'qm' not found. Run this script on the Proxmox/PXVIRT host (as root)."
    fi

    check_proxmox_daemons
    check_host_ram
    resolve_ssh_key

    if qm status "$VMID" &>/dev/null; then
        if [[ "$RECREATE" -eq 1 ]]; then
            remove_existing_vm
        else
            die "VM ${VMID} already exists. Use --recreate or a different VMID."
        fi
    fi

    if ! pvesm status | awk '{print $1}' | grep -qx "$STORAGE"; then
        die "Storage '${STORAGE}' not found. Prefer 'local' on this host (no local-lvm)."
    fi
}

download_debian_image() {
    local image_path="${DOWNLOAD_DIR}/${DEBIAN_IMAGE}"

    mkdir -p "$DOWNLOAD_DIR"

    if [[ -f "$image_path" ]]; then
        log "Debian image already exists at ${image_path}, skipping download."
        return
    fi

    log "Downloading ${DEBIAN_IMAGE}..."
    wget -q --show-progress -O "${image_path}.partial" "$DEBIAN_IMAGE_URL"
    mv "${image_path}.partial" "$image_path"
    log "Image ready at ${image_path}"
}

create_vm() {
    local image_path="${DOWNLOAD_DIR}/${DEBIAN_IMAGE}"
    local tmp_key
    # Directory storage (local): EFI = disk-0, imported OS = disk-1
    local scsi_disk="${STORAGE}:${VMID}/vm-${VMID}-disk-1.raw"

    log "Creating VM ${VMID} (${VM_NAME})..."

    qm create "$VMID" \
        --name "$VM_NAME" \
        --arch aarch64 \
        --ostype l26 \
        --machine virt \
        --cores "$CORES" \
        --memory "$MEMORY" \
        --balloon "$BALLOON" \
        --net0 "virtio,bridge=${BRIDGE}" \
        --bios ovmf \
        --agent enabled=1 \
        --onboot 1 \
        --startup "order=${STARTUP_ORDER}" \
        --scsihw virtio-scsi-pci \
        --serial0 socket \
        --vga serial0

    qm set "$VMID" --efidisk0 "${STORAGE}:1,format=raw,efitype=4m,pre-enrolled-keys=0"

    log "Importing Debian cloud image to ${STORAGE}..."
    qm importdisk "$VMID" "$image_path" "$STORAGE" --format raw

    log "Attaching OS disk, cloud-init (SCSI), and resizing to ${DISK_SIZE}..."
    qm set "$VMID" \
        --scsi0 "$scsi_disk" \
        --scsi1 "${STORAGE}:cloudinit" \
        --boot "order=scsi0"

    qm resize "$VMID" scsi0 "$DISK_SIZE"

    tmp_key="$(mktemp)"
    printf '%s\n' "$SSH_PUBLIC_KEY" > "$tmp_key"
    qm set "$VMID" \
        --ciuser "$CI_USER" \
        --sshkeys "$tmp_key" \
        --ipconfig0 "ip=${VM_IP},gw=${GATEWAY}" \
        --nameserver "$NAMESERVER" \
        --searchdomain "lan"
    rm -f "$tmp_key"

    qm cloudinit update "$VMID" 2>/dev/null || true

    log "VM ${VMID} created (disk ${DISK_SIZE}, IP ${VM_IP}, user ${CI_USER})."
}

start_vm() {
    log "Starting VM ${VMID}..."
    qm start "$VMID"
    log "VM ${VMID} is running."
    log "Wait ~60–90s for cloud-init, then: ssh ${CI_USER}@${VM_IP%%/*}"
    log "Note MAC (for DHCP reservation): qm config ${VMID} | grep net0"
    log "Next: install WireGuard + Caddy (docs/wireguard.md)."
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log "=== WireGuard VM provisioning (Debian 12 ARM64 / cloud-init) ==="
    log "VMID: ${VMID} | Name: ${VM_NAME} | Cores: ${CORES} | RAM: ${MEMORY}MiB (balloon ${BALLOON})"
    log "Storage: ${STORAGE} | Disk: ${DISK_SIZE} | Bridge: ${BRIDGE}"
    log "IP: ${VM_IP} | GW: ${GATEWAY} | DNS (temp): ${NAMESERVER} | User: ${CI_USER}"
    echo ""

    check_prerequisites
    download_debian_image
    create_vm
    start_vm

    log "=== Provisioning complete ==="
}

main "$@"
