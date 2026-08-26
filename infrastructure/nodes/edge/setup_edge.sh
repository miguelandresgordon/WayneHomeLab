#!/usr/bin/env bash
# ==============================================================================
# setup_edge.sh — RPi 3b Edge Node Setup (DietPi + Wyoming Satellite)
#
# Prepares a Raspberry Pi 3b running DietPi as the voice pipeline edge node
# with Docker, SSD mount, and Wyoming satellite dependencies.
#
# Usage: sudo bash setup_edge.sh
#
# Prerequisites:
#   - DietPi installed and booted on RPi 3b
#   - SSD connected via USB
#   - Root or sudo access
#   - Internet connectivity
# ==============================================================================
set -euo pipefail

LOG_FILE="/var/log/setup_edge.log"

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
SSD_DEVICE="${SSD_DEVICE:-/dev/sda1}"
SSD_MOUNT="${SSD_MOUNT:-/mnt/ssd}"
DOCKER_DATA_DIR="${SSD_MOUNT}/docker"

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
    log "Architecture: ${arch} (expected: aarch64 or armv7l)"
}

install_dependencies() {
    log "Updating packages..."
    apt-get update -qq

    log "Installing base dependencies..."
    apt-get install -y -qq \
        curl \
        wget \
        git \
        htop \
        jq \
        alsa-utils \
        python3 \
        python3-pip \
        python3-venv

    log "Dependencies installed."
}

setup_ssd_mount() {
    log "Configuring SSD mount..."

    if mountpoint -q "$SSD_MOUNT" 2>/dev/null; then
        log "SSD already mounted at ${SSD_MOUNT}, skipping."
        return
    fi

    if [[ ! -b "$SSD_DEVICE" ]]; then
        log "WARNING: SSD device ${SSD_DEVICE} not found. Skipping SSD setup."
        log "Set SSD_DEVICE env var to the correct device path."
        return
    fi

    mkdir -p "$SSD_MOUNT"

    # Check if already in fstab
    if grep -q "$SSD_MOUNT" /etc/fstab; then
        log "SSD already in fstab, skipping."
    else
        # Get UUID for reliable mounting
        local uuid
        uuid="$(blkid -s UUID -o value "$SSD_DEVICE" 2>/dev/null || true)"

        if [[ -n "$uuid" ]]; then
            echo "UUID=${uuid} ${SSD_MOUNT} ext4 defaults,noatime 0 2" >> /etc/fstab
            log "Added SSD to fstab (UUID=${uuid})."
        else
            echo "${SSD_DEVICE} ${SSD_MOUNT} ext4 defaults,noatime 0 2" >> /etc/fstab
            log "Added SSD to fstab (device path, UUID not available)."
        fi
    fi

    mount -a
    log "SSD mounted at ${SSD_MOUNT}."
}

install_docker() {
    log "Installing Docker..."

    if command -v docker &>/dev/null; then
        log "Docker already installed: $(docker --version)"
        return
    fi

    curl -fsSL https://get.docker.com | sh

    # Move Docker data to SSD if mounted
    if mountpoint -q "$SSD_MOUNT" 2>/dev/null; then
        log "Configuring Docker to use SSD storage at ${DOCKER_DATA_DIR}..."
        mkdir -p "$DOCKER_DATA_DIR"
        mkdir -p /etc/docker

        cat > /etc/docker/daemon.json <<EOF
{
    "data-root": "${DOCKER_DATA_DIR}",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
    fi

    # Add dietpi user to docker group
    usermod -aG docker dietpi 2>/dev/null || true

    systemctl enable docker
    systemctl restart docker

    log "Docker installed and configured."
}

install_docker_compose() {
    log "Installing Docker Compose plugin..."

    if docker compose version &>/dev/null; then
        log "Docker Compose already available: $(docker compose version)"
        return
    fi

    apt-get install -y -qq docker-compose-plugin

    log "Docker Compose installed."
}

prepare_voice_pipeline_dirs() {
    log "Creating voice pipeline directories..."

    local base_dir="${SSD_MOUNT}/voice-pipeline"
    if ! mountpoint -q "$SSD_MOUNT" 2>/dev/null; then
        base_dir="/opt/voice-pipeline"
    fi

    mkdir -p "${base_dir}/whisper/data"
    mkdir -p "${base_dir}/piper/data"

    log "Voice pipeline directories ready at ${base_dir}."
}

configure_audio() {
    log "Configuring audio devices for Wyoming satellite..."

    # Load sound modules
    modprobe snd_bcm2835 2>/dev/null || true

    # Ensure audio group membership
    usermod -aG audio dietpi 2>/dev/null || true

    log "Audio configuration complete."
}

print_summary() {
    log ""
    log "==========================================="
    log "  RPi 3b Edge Node Setup Complete"
    log "==========================================="
    log "  SSD:       ${SSD_MOUNT}"
    log "  Docker:    $(docker --version 2>/dev/null || echo 'not available')"
    log "  Audio:     Configured"
    log ""
    log "  Next steps:"
    log "  1. Copy voice-pipeline/ to ~/voice-pipeline/"
    log "  2. cp .env.example .env and edit values"
    log "  3. docker compose up -d"
    log "  4. Configure Wyoming integration in HA"
    log "==========================================="
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log "=== RPi 3b Edge Node Setup ==="

    check_root
    check_architecture
    install_dependencies
    setup_ssd_mount
    install_docker
    install_docker_compose
    prepare_voice_pipeline_dirs
    configure_audio
    print_summary
}

main "$@"
