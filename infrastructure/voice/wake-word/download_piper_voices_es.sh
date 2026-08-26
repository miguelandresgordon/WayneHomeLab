#!/usr/bin/env bash
# download_piper_voices_es.sh — Descarga voces Piper españolas para entrenamiento MWW
#
# Uso: ./download_piper_voices_es.sh
# Destino: ~/Proyectos/microWakeWord-Trainer-AppleSilicon/piper-sample-generator/voices/

set -euo pipefail

TRAINER_DIR="${MWW_TRAINER_DIR:-$HOME/Proyectos/microWakeWord-Trainer-AppleSilicon}"
VOICES_DIR="$TRAINER_DIR/piper-sample-generator/voices"
PYTHON_BIN="${PYTHON_BIN:-$TRAINER_DIR/.venv/bin/python}"

# Voces españolas recomendadas (multi-speaker / variantes regionales)
ES_VOICES=(
  "es_ES-davefx-medium"
  "es_ES-sharvard-medium"
  "es_ES-carlfm-x_low"
  "es_MX-ald-medium"
  "es_AR-daniela-high"
)

log() { printf '[download-piper-es] %s\n' "$*"; }

if [[ ! -x "$PYTHON_BIN" ]]; then
  log "Trainer venv no encontrado. Ejecuta primero setup_trainer_macos.sh train (fallará) o train_microwakeword setup."
  exit 1
fi

mkdir -p "$VOICES_DIR"
cd "$TRAINER_DIR"

log "Descargando ${#ES_VOICES[@]} voces Piper a $VOICES_DIR"
for voice in "${ES_VOICES[@]}"; do
  if [[ -f "$VOICES_DIR/${voice}.onnx" ]]; then
    log "  ✓ $voice (ya existe)"
    continue
  fi
  log "  ↓ $voice"
  "$PYTHON_BIN" -m piper.download_voices "$voice" --download-dir "$VOICES_DIR"
done

count="$(find "$VOICES_DIR" -name 'es_*.onnx' 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$count" -eq 0 ]]; then
  log "❌ No se descargaron voces es_*.onnx"
  exit 1
fi

log "✅ $count voces españolas listas en $VOICES_DIR"
