#!/usr/bin/env bash
# configure_ha_mariano.sh — Checklist post-flash para wake word Mariano en HA
#
# Ejecutar tras flash OTA con modelo mariano instalado.
# Requiere acceso web a http://192.168.1.110:8123

set -euo pipefail

HA_URL="${HA_URL:-http://192.168.1.110:8123}"

cat <<EOF
=== Configuración HA — Wake word Mariano ===

1. Pipeline de voz (Configuración → Asistentes de voz):
   - Idioma: Español
   - STT: openai_whisper_cloud (whisper-large-v3-turbo)
   - TTS: Wyoming Piper (core-piper:10200)
   - Conversation: Home Assistant

2. Satellite1 (Configuración → Dispositivos → ESPHome → satellite1_c7ffe4):
   - Voice pipeline: [tu pipeline Groq+Piper]
   - Wake word: Mariano
   - Wake word sensitivity: Slightly sensitive

3. Exponer entidades (Configuración → Asistentes de voz → Exponer):
   - light.lampara → alias "lámpara"
   - light.bombilla_antela → alias "bombilla"

4. Calibración probability_cutoff (ESPHome YAML):
   - Falsos positivos TV → subir a 92%
   - No detecta tu voz → bajar a 75%
   Ver: infrastructure/voice/wake-word/satellite1_mariano_overlay.yaml

5. Desplegar automations + debug STT:
   HA_HOST=192.168.1.110 ./infrastructure/voice/wake-word/deploy_ha_voice_config.sh

HA URL: ${HA_URL}
EOF

if curl -sf --max-time 3 "${HA_URL}/" >/dev/null 2>&1; then
  echo "✅ Home Assistant accesible"
else
  echo "⚠️  Home Assistant no accesible desde esta máquina — ejecuta pasos manualmente en LAN"
fi
