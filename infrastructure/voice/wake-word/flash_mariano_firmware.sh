#!/usr/bin/env bash
# flash_mariano_firmware.sh — Pasos para instalar wake word Mariano en Satellite1
#
# Prerrequisitos:
#   - mariano.tflite + mariano.json en models/ (copy_model_from_trainer.sh)
#   - serve_model.sh corriendo O modelo en URL pública
#   - ESPHome Device Builder en HA

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '192.168.1.XXX')"
MODEL_URL="http://${MAC_IP}:8765/mariano.json"

if [[ ! -f "$SCRIPT_DIR/models/mariano.json" ]]; then
  echo "❌ Ejecuta primero: ./copy_model_from_trainer.sh"
  exit 1
fi

cat <<EOF
=== Instalar wake word Mariano en Satellite1 ===

Model URL: ${MODEL_URL}

1. Inicia servidor de modelos (otra terminal):
   ./infrastructure/voice/wake-word/serve_model.sh

2. HA → Complementos → ESPHome Device Builder → Open Web UI

3. SHOW → Take Control → Satellite1 (satellite1_c7ffe4)

4. EDIT → en micro_wake_word.models, añadir ANTES de okay_nabu:

   - model: ${MODEL_URL}
     id: mariano
     probability_cutoff: 85%

5. Opcional — voice_assistant (mejor STT):
   noise_suppression_level: 2
   auto_gain: 12 dBFS
   volume_multiplier: 2.0

   Ver: infrastructure/voice/wake-word/satellite1_mariano_overlay.yaml

6. INSTALL → esperar compilación + OTA

7. HA → Dispositivos → ESPHome → Satellite1 → Configuración:
   - Voice pipeline: (Groq + Piper)
   - Wake word: Mariano
   - Wake word sensitivity: Slightly sensitive

8. Probar. Ajustar probability_cutoff si hay falsos positivos o misses.

Documentación: docs/wake-word-mariano.md
EOF
