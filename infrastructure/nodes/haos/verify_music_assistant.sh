#!/usr/bin/env bash
# ==============================================================================
# verify_music_assistant.sh — Smoke-test Music Assistant add-on on HAOS
#
# Usage:
#   bash infrastructure/nodes/haos/verify_music_assistant.sh
#   HA_HOST=192.168.1.110 bash infrastructure/nodes/haos/verify_music_assistant.sh
#
# Requires SSH as root@HA_HOST (Terminal & SSH add-on). Does not change config.
# Exit 0 if add-on is started, UI responds, logs since last start have no
# Smart Fades / torch download / shutdown, and Whisper stays stopped.
# ==============================================================================
set -euo pipefail

HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
MA_SLUG="${MA_SLUG:-d5369777_music_assistant}"
WHISPER_SLUG="${WHISPER_SLUG:-core_whisper}"
MA_UI_URL="${MA_UI_URL:-http://${HA_HOST}:8095/}"
failed=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        log "ERROR: missing command: $1"
        exit 1
    }
}

haos() {
    ssh -o BatchMode=yes -o ConnectTimeout=8 "${HA_USER}@${HA_HOST}" "$@"
}

need_cmd ssh
need_cmd curl
need_cmd ping

log "=== Music Assistant verify @ ${HA_HOST} (${MA_SLUG}) ==="

if ping -c 1 -W 2 "$HA_HOST" >/dev/null 2>&1 || ping -c 1 -t 2 "$HA_HOST" >/dev/null 2>&1; then
    log "OK: ping ${HA_HOST}"
else
    log "FAIL: ping ${HA_HOST} (HAOS down?)"
    exit 1
fi

if ! haos "true" >/dev/null 2>&1; then
    log "FAIL: SSH ${HA_USER}@${HA_HOST}"
    exit 1
fi

ma_json="$(haos "ha apps info ${MA_SLUG} --raw-json")"
ma_state="$(printf '%s' "$ma_json" | jq -r '.data.state')"
ma_version="$(printf '%s' "$ma_json" | jq -r '.data.version')"
ma_log_level="$(printf '%s' "$ma_json" | jq -r '.data.options.log_level')"
ma_safe="$(printf '%s' "$ma_json" | jq -r '.data.options.safe_mode')"

if [[ "$ma_state" == "started" ]]; then
    log "OK: add-on ${MA_SLUG} started (v${ma_version})"
else
    log "FAIL: add-on state=${ma_state} (expected started)"
    failed=1
fi

if [[ "$ma_safe" == "false" ]]; then
    log "OK: safe_mode=false"
else
    log "FAIL: safe_mode=${ma_safe} (providers will not load)"
    failed=1
fi

if [[ "$ma_log_level" == "info" || "$ma_log_level" == "debug" ]]; then
    log "OK: log_level=${ma_log_level}"
else
    log "WARN: log_level=${ma_log_level} (error oculta el arranque; usar info)"
fi

mem_bytes="$(haos "ha apps stats ${MA_SLUG} --raw-json" | jq -r '.data.memory_usage')"
if [[ "$mem_bytes" =~ ^[0-9]+$ ]]; then
    mem_mib=$((mem_bytes / 1048576))
    if [[ "$mem_mib" -lt 800 ]]; then
        log "OK: memory ${mem_mib} MiB (<800; torch/Smart Fades no parece cargado)"
    else
        log "FAIL: memory ${mem_mib} MiB (>=800; posible torch/Smart Fades)"
        failed=1
    fi
else
    log "WARN: no se pudo leer memory_usage"
fi

ui_code="$(curl -sS -m 8 -o /dev/null -w '%{http_code}' "$MA_UI_URL" || true)"
if [[ "$ui_code" == "200" ]]; then
    log "OK: GET ${MA_UI_URL} → ${ui_code}"
else
    log "FAIL: GET ${MA_UI_URL} → ${ui_code:-curl-error}"
    failed=1
fi

# Logs since the last start: first "Loaded player provider Universal Player" from the end.
logs="$(haos "ha apps logs ${MA_SLUG}" 2>/dev/null || true)"
last_start="$(printf '%s\n' "$logs" | grep -n 'Loaded player provider Universal Player' | tail -n1 | cut -d: -f1)"
if [[ -n "${last_start}" ]]; then
    recent="$(printf '%s\n' "$logs" | tail -n "+${last_start}")"
    if printf '%s\n' "$recent" | grep -q 'Loaded audio_analysis provider Smart Fades'; then
        log "FAIL: Smart Fades se cargó en el último arranque (desactivar provider)"
        failed=1
    else
        log "OK: último arranque sin Smart Fades"
    fi
    if printf '%s\n' "$recent" | grep -q 'beat_this'; then
        log "FAIL: descarga torch beat_this en el último arranque"
        failed=1
    else
        log "OK: último arranque sin beat_this/torch"
    fi
    if printf '%s\n' "$recent" | grep -q 'shutdown requested'; then
        log "FAIL: shutdown requested tras el último arranque"
        failed=1
    else
        log "OK: último arranque sin shutdown requested"
    fi
    if printf '%s\n' "$recent" | grep -q 'Successfully logged in to Spotify'; then
        log "OK: Spotify autenticado"
    else
        log "WARN: no se vio login Spotify en el último arranque"
    fi
    if printf '%s\n' "$recent" | grep -qi 'satellite1'; then
        log "OK: satellite1 registrado"
    else
        log "WARN: no se vio satellite1 en el último arranque"
    fi
else
    log "WARN: no se encontró marca de arranque en logs (add-on recién instalado?)"
fi

wh_json="$(haos "ha apps info ${WHISPER_SLUG} --raw-json")"
wh_state="$(printf '%s' "$wh_json" | jq -r '.data.state')"
wh_boot="$(printf '%s' "$wh_json" | jq -r '.data.boot')"
if [[ "$wh_state" == "stopped" && "$wh_boot" == "manual" ]]; then
    log "OK: Whisper ${wh_state} boot=${wh_boot}"
else
    log "FAIL: Whisper state=${wh_state} boot=${wh_boot} (debe estar stopped / manual; STT=Groq)"
    failed=1
fi

if [[ "$failed" -eq 0 ]]; then
    log "=== Music Assistant verify: PASS ==="
    exit 0
fi
log "=== Music Assistant verify: FAIL ==="
exit 1
