#!/usr/bin/env bash
# serve_model.sh — Sirve mariano.json + mariano.tflite en la LAN para ESPHome OTA
#
# Uso:
#   ./serve_model.sh /path/to/trained_wake_words
#   ./serve_model.sh   # usa WayneHomeLab/infrastructure/voice/wake-word/models/
#
# El Satellite1 debe poder alcanzar http://<IP_MAC>:8765/mariano.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${1:-$SCRIPT_DIR/models}"
PORT="${MWW_SERVE_PORT:-8765}"
HOST="${MWW_SERVE_HOST:-0.0.0.0}"

if [[ ! -f "$MODELS_DIR/mariano.json" ]] || [[ ! -f "$MODELS_DIR/mariano.tflite" ]]; then
  echo "❌ Faltan mariano.json o mariano.tflite en: $MODELS_DIR"
  echo "   Copia los artefactos del trainer:"
  echo "   cp ~/Proyectos/microWakeWord-Trainer-AppleSilicon/trained_wake_words/mariano.* $MODELS_DIR/"
  exit 1
fi

LOCAL_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '127.0.0.1')"

echo "Sirviendo modelos desde $MODELS_DIR"
echo "  JSON:   http://${LOCAL_IP}:${PORT}/mariano.json"
echo "  TFLite: http://${LOCAL_IP}:${PORT}/mariano.tflite"
echo "Pulsa Ctrl+C para detener."

cd "$MODELS_DIR"
python3 -m http.server "$PORT" --bind "$HOST"
