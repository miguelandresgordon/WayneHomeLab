#!/usr/bin/env bash
# sync_satellite1_api_secret.sh — Copia noise_psk de Satellite1 a secrets ESPHome.
#
# Fuentes (primera que exista):
#   1) ~/.ha-sat1-test/config/.storage/esphome.encryption_keys
#   2) HAOS /config/.storage/core.config_entries (domain esphome, MAC)
#
# Destinos:
#   - infrastructure/voice/wake-word/esphome/secrets.yaml (gitignored)
#   - HAOS /config/esphome/secrets.yaml (merge; no pisa wifi_ssid/password)
#
# Uso:
#   HA_HOST=192.168.1.110 ./infrastructure/voice/wake-word/sync_satellite1_api_secret.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/config}"
MAC="${SATELLITE1_MAC:-3c:0f:02:c7:ff:e4}"
LOCAL_KEYS="${ESPHOME_ENCRYPTION_KEYS:-$HOME/.ha-sat1-test/config/.storage/esphome.encryption_keys}"
LOCAL_SECRETS="$REPO_ROOT/infrastructure/voice/wake-word/esphome/secrets.yaml"
FIRMWARE_YAML="$REPO_ROOT/infrastructure/voice/wake-word/esphome/satellite1-c7ffe4.yaml"

log() { printf '[sync-sat1-api] %s\n' "$*"; }

python3 - "$LOCAL_KEYS" "$MAC" "$LOCAL_SECRETS" <<'PY'
import json
import sys
from pathlib import Path

keys_path = Path(sys.argv[1])
mac = sys.argv[2]
dest = Path(sys.argv[3])
if not keys_path.is_file():
    sys.exit(f"missing encryption_keys file: {keys_path}")
raw = json.loads(keys_path.read_text(encoding="utf-8"))
key = raw.get("data", {}).get("keys", {}).get(mac)
if not key or not isinstance(key, str):
    sys.exit(f"no Noise PSK for MAC {mac}")
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(
    "# gitignored — Noise PSK of live Satellite1 (do not commit)\n"
    f'api_encryption_key: "{key}"\n',
    encoding="utf-8",
)
print(f"local secrets written ({len(key)} chars)")
PY

if ! ping -c 1 -W 2 "$HA_HOST" >/dev/null 2>&1; then
  log "❌ No hay respuesta de $HA_HOST — secrets locales OK; copia a HAOS a mano"
  exit 1
fi

log "Copiando firmware YAML a ${HA_USER}@${HA_HOST}:${HA_CONFIG}/esphome/"
ssh "${HA_USER}@${HA_HOST}" "mkdir -p ${HA_CONFIG}/esphome"
scp "$FIRMWARE_YAML" "${HA_USER}@${HA_HOST}:${HA_CONFIG}/esphome/satellite1-c7ffe4.yaml"
scp "$LOCAL_SECRETS" "${HA_USER}@${HA_HOST}:/tmp/satellite1_api_secret.yaml"

if ! grep -qE '^api_encryption_key:' "$LOCAL_SECRETS"; then
  log "❌ secrets locales sin api_encryption_key"
  exit 1
fi

# HAOS SSH add-on often has no python3. Merge with awk (no overwrite of wifi_*).
ssh "${HA_USER}@${HA_HOST}" "HA_CONFIG='${HA_CONFIG}' sh -s" <<'REMOTE'
set -eu
DEST="${HA_CONFIG}/esphome/secrets.yaml"
SRC=/tmp/satellite1_api_secret.yaml
mkdir -p "${HA_CONFIG}/esphome"
LINE=$(grep -E '^api_encryption_key:' "$SRC")
if [ -z "$LINE" ]; then
  echo 'missing api_encryption_key in fragment' >&2
  exit 1
fi
if [ -f "$DEST" ]; then
  awk -v line="$LINE" 'BEGIN{done=0} /^api_encryption_key:/{print line; done=1; next} {print} END{if(!done) print line}' "$DEST" > "$DEST.tmp"
  mv "$DEST.tmp" "$DEST"
else
  printf '%s\n' "$LINE" > "$DEST"
fi
rm -f "$SRC"
echo 'haos esphome/secrets.yaml merged (api_encryption_key)'
REMOTE

log "✅ YAML + api_encryption_key en HAOS. Cancela el Install colgado → Clean Build Files → Install Wirelessly."
