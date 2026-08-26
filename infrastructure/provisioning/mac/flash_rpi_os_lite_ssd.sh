#!/usr/bin/env bash
# ==============================================================================
# flash_rpi_os_lite_ssd.sh
#
# Headless-friendly helper to flash Raspberry Pi OS Lite image to a USB SSD
# from macOS and create first-boot SSH/user configuration.
#
# Usage:
#   bash flash_rpi_os_lite_ssd.sh --target /dev/diskX --hostname waynelab-core \
#     --username pi --password 'CHANGE_ME' [--wifi-ssid SSID --wifi-psk PASS]
# ==============================================================================
set -euo pipefail

IMAGE_PATH="${IMAGE_PATH:-}"
TARGET_DISK=""
HOSTNAME="waynelab-core"
USERNAME="pi"
PASSWORD=""
WIFI_SSID=""
WIFI_PSK=""

usage() {
  cat <<'EOF'
Usage:
  bash flash_rpi_os_lite_ssd.sh --target /dev/diskX --hostname waynelab-core \
    --username pi --password 'CHANGE_ME' [--wifi-ssid SSID --wifi-psk PASS]

Notes:
- Requires a pre-downloaded Raspberry Pi OS Lite .img or .img.xz file.
- Set IMAGE_PATH env var to the image file path.
- This script will erase the target disk.
EOF
}

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: Missing command '$1'"
    exit 1
  }
}

hash_password() {
  # OpenSSL format accepted by userconf.txt: username:hash
  # shellcheck disable=SC2005
  echo "$(printf '%s' "$PASSWORD" | openssl passwd -6 -stdin)"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target) TARGET_DISK="$2"; shift 2 ;;
      --hostname) HOSTNAME="$2"; shift 2 ;;
      --username) USERNAME="$2"; shift 2 ;;
      --password) PASSWORD="$2"; shift 2 ;;
      --wifi-ssid) WIFI_SSID="$2"; shift 2 ;;
      --wifi-psk) WIFI_PSK="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done
}

check_inputs() {
  [[ -n "$TARGET_DISK" ]] || { echo "ERROR: --target is required"; exit 1; }
  [[ -n "$PASSWORD" ]] || { echo "ERROR: --password is required"; exit 1; }
  [[ -n "$IMAGE_PATH" ]] || { echo "ERROR: IMAGE_PATH env var is required"; exit 1; }
  [[ -f "$IMAGE_PATH" ]] || { echo "ERROR: IMAGE_PATH does not exist: $IMAGE_PATH"; exit 1; }
}

decompress_if_needed() {
  local img="$IMAGE_PATH"
  if [[ "$img" == *.xz ]]; then
    require_cmd xz
    log "Decompressing image..."
    xz -dk "$img"
    IMAGE_PATH="${img%.xz}"
  fi
}

flash_image() {
  log "Unmounting target disk ${TARGET_DISK}..."
  diskutil unmountDisk force "$TARGET_DISK" >/dev/null

  local raw_disk
  raw_disk="$(echo "$TARGET_DISK" | sed 's#/dev/disk#/dev/rdisk#')"

  log "Flashing image to ${raw_disk} (this can take several minutes)..."
  sudo dd if="$IMAGE_PATH" of="$raw_disk" bs=8m conv=sync status=progress
  sync
  diskutil eject "$TARGET_DISK" >/dev/null
}

configure_boot_partition() {
  log "Re-mounting disk to configure headless boot..."
  diskutil mountDisk "$TARGET_DISK" >/dev/null

  local boot_mount
  boot_mount="$(diskutil info "${TARGET_DISK}s1" | awk -F': ' '/Mount Point/ {print $2}')"
  [[ -n "$boot_mount" ]] || { echo "ERROR: Could not find boot mount point"; exit 1; }

  log "Configuring boot partition at ${boot_mount}..."

  touch "${boot_mount}/ssh"
  printf '%s:%s\n' "$USERNAME" "$(hash_password)" > "${boot_mount}/userconf.txt"
  printf '%s\n' "$HOSTNAME" > "${boot_mount}/hostname"

  if [[ -n "$WIFI_SSID" && -n "$WIFI_PSK" ]]; then
    cat > "${boot_mount}/wpa_supplicant.conf" <<EOF
country=ES
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
  ssid="${WIFI_SSID}"
  psk="${WIFI_PSK}"
  key_mgmt=WPA-PSK
}
EOF
  fi

  diskutil eject "$TARGET_DISK" >/dev/null
  log "Done. Insert SSD into Pi5 and boot."
}

main() {
  parse_args "$@"
  check_inputs
  require_cmd diskutil
  require_cmd dd
  require_cmd openssl
  decompress_if_needed
  flash_image
  configure_boot_partition
}

main "$@"
