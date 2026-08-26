#!/usr/bin/env bash
# ==============================================================================
# setup_host.sh — RPi 5 Post-Install Bootstrap (Proxmox Host)
#
# Prepares a Raspberry Pi 5 running Raspberry Pi OS Lite 64-bit as a
# Proxmox VE virtualization host with bridge networking and kernel tuning.
#
# Usage: sudo bash setup_host.sh
#
# Prerequisites:
#   - Fresh Raspberry Pi OS Lite 64-bit installation
#   - Root or sudo access
#   - Internet connectivity
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/setup_host.log"

# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "ERROR: This script must be run as root (use sudo)."
        exit 1
    fi
}

check_architecture() {
    local arch
    arch="$(uname -m)"
    if [[ "$arch" != "aarch64" ]]; then
        log "WARNING: Expected aarch64 architecture, got ${arch}."
    fi
    log "Architecture: ${arch}"
}

install_dependencies() {
    log "Updating package lists..."
    apt-get update -qq

    log "Installing base dependencies..."
    apt-get install -y -qq \
        curl \
        wget \
        git \
        htop \
        iotop \
        tmux \
        vim \
        bridge-utils \
        net-tools \
        dnsutils \
        jq \
        unzip \
        xz-utils \
        lm-sensors \
        python3 \
        python3-pip

    log "Dependencies installed."
}

configure_bridge_networking() {
    log "Configuring bridge networking (vmbr0)..."

    local bridge_conf="/etc/network/interfaces.d/vmbr0"
    mkdir -p /etc/network/interfaces.d

    if [[ -f "$bridge_conf" ]]; then
        log "Bridge config already exists at ${bridge_conf}, skipping."
        return
    fi

    # Detect primary network interface
    local primary_iface
    primary_iface="$(ip route show default | awk '/default/ {print $5}' | head -1)"

    if [[ -z "$primary_iface" ]]; then
        log "ERROR: Could not detect primary network interface."
        exit 1
    fi

    log "Primary interface detected: ${primary_iface}"

    cat > "$bridge_conf" <<EOF
# Bridge interface for Proxmox VMs
# Primary interface: ${primary_iface}

auto vmbr0
iface vmbr0 inet dhcp
    bridge_ports ${primary_iface}
    bridge_stp off
    bridge_fd 0
EOF

    log "Bridge configuration written to ${bridge_conf}."
    log "NOTE: Network will be reconfigured on next reboot."
}

apply_kernel_tuning() {
    log "Applying kernel tuning parameters..."

    local sysctl_src="${SCRIPT_DIR}/sysctl.conf"
    local sysctl_dest="/etc/sysctl.d/99-waynelab.conf"

    if [[ -f "$sysctl_src" ]]; then
        cp "$sysctl_src" "$sysctl_dest"
    else
        cat > "$sysctl_dest" <<'EOF'
# WayneHomelab — Kernel tuning for Proxmox on RPi 5

# Reduce swap usage (prefer RAM)
vm.swappiness=10

# Increase inotify watchers for HA
fs.inotify.max_user_watches=524288
fs.inotify.max_user_instances=512

# Network tuning for bridge
net.bridge.bridge-nf-call-iptables=1
net.bridge.bridge-nf-call-ip6tables=1

# Memory overcommit (needed for KVM)
vm.overcommit_memory=1

# Increase max open files
fs.file-max=2097152

# Network performance
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
EOF
    fi

    sysctl --system > /dev/null 2>&1
    log "Kernel parameters applied."
}

load_kvm_modules() {
    log "Configuring KVM kernel modules..."

    # Ensure modules load on boot
    cat > /etc/modules-load.d/kvm.conf <<EOF
# KVM modules for Proxmox on RPi 5 (ARM64)
kvm
EOF

    # Load modules now
    modprobe kvm 2>/dev/null || log "WARNING: KVM module not available yet (may need Proxmox kernel)."

    log "KVM modules configured."
}

configure_ssh_hardening() {
    log "Hardening SSH configuration..."

    local sshd_conf="/etc/ssh/sshd_config.d/99-waynelab.conf"

    cat > "$sshd_conf" <<EOF
# WayneHomelab SSH hardening
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
EOF

    log "SSH hardened. Ensure your public key is in ~/.ssh/authorized_keys before rebooting."
}

setup_automatic_updates() {
    log "Configuring unattended security updates..."

    apt-get install -y -qq unattended-upgrades

    cat > /etc/apt/apt.conf.d/20auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

    log "Automatic security updates enabled."
}

print_summary() {
    log ""
    log "==========================================="
    log "  RPi 5 Host Setup Complete"
    log "==========================================="
    log "  Bridge:    vmbr0 (DHCP)"
    log "  Kernel:    Tuned for virtualization"
    log "  SSH:       Key-only authentication"
    log "  Updates:   Automatic security updates"
    log ""
    log "  Next steps:"
    log "  1. Reboot to apply network changes"
    log "  2. Install Proxmox VE (see docs/setup-guide.md)"
    log "  3. Run create_haos_vm.sh to provision HAOS"
    log "==========================================="
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log "=== RPi 5 Host Setup ==="

    check_root
    check_architecture
    install_dependencies
    configure_bridge_networking
    apply_kernel_tuning
    load_kvm_modules
    configure_ssh_hardening
    setup_automatic_updates
    print_summary
}

main "$@"
