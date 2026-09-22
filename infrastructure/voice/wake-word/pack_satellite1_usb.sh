#!/usr/bin/env bash
# pack_satellite1_usb.sh — Copia el kit de flash USB (bootloader) a un pendrive.
#
# Un pendrive NO flashea el Satellite1. Sirve para llevar YAML+secrets a un
# PC/Mac y flashear por el USB-C del dispositivo. Ver esphome/USB_BOOTLOADER.md
#
# Uso:
#   USB_VOLUME=/Volumes/MIGUEL ./infrastructure/voice/wake-word/pack_satellite1_usb.sh
#   ./infrastructure/voice/wake-word/pack_satellite1_usb.sh /Volumes/MIGUEL/wayne-satellite1-usb-flash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESPHOME_DIR="$SCRIPT_DIR/esphome"
USB_VOLUME="${USB_VOLUME:-/Volumes/MIGUEL}"
DEST="${1:-$USB_VOLUME/wayne-satellite1-usb-flash}"

log() { printf '[pack-sat1-usb] %s\n' "$*"; }

if [[ ! -d "$USB_VOLUME" && "$DEST" == "$USB_VOLUME/"* ]]; then
  log "❌ Pendrive no montado: $USB_VOLUME"
  log "   Enchufa el USB y espera a que aparezca en /Volumes"
  exit 1
fi

SECRETS_SRC=""
for candidate in \
  "/Volumes/config/esphome/secrets.yaml" \
  "$ESPHOME_DIR/secrets.yaml"
do
  if [[ -f "$candidate" ]] && grep -qE '^api_encryption_key:' "$candidate"; then
    SECRETS_SRC="$candidate"
    break
  fi
done

if [[ -z "$SECRETS_SRC" ]]; then
  log "❌ No hay secrets.yaml con api_encryption_key (local gitignored o Samba /Volumes/config)"
  exit 1
fi

mkdir -p "$DEST"
cp "$ESPHOME_DIR/satellite1-c7ffe4.yaml" "$DEST/satellite1-c7ffe4.yaml"
cp "$SCRIPT_DIR/satellite1_mariano_overlay.yaml" "$DEST/satellite1_mariano_overlay.yaml"
cp "$ESPHOME_DIR/secrets.yaml.example" "$DEST/secrets.yaml.example"
cp "$ESPHOME_DIR/USB_BOOTLOADER.md" "$DEST/USB_BOOTLOADER.md"
cp "$ESPHOME_DIR/USB_BOOTLOADER.md" "$DEST/LEEME.txt"
cp "$SECRETS_SRC" "$DEST/secrets.yaml"

log "Kit en $DEST"
log "  yaml overlay example LEEME.txt USB_BOOTLOADER.md"
log "  secrets.yaml copiado desde $SECRETS_SRC (no commitear)"
log "Siguiente: cable USB-C del Satellite1 → PC/Mac → Install → Plug into this computer"
log "Ver $DEST/LEEME.txt"
