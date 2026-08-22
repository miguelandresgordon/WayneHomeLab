#!/usr/bin/env bash
# flash_capture_firmware.sh — Guía para flashear firmware de captura en Satellite1
#
# Requiere: trainer UI corriendo (setup_trainer_macos.sh ui)
# Satellite1 accesible en la LAN (192.168.1.85)

set -euo pipefail

SAT_IP="${SAT_IP:-192.168.1.85}"
TRAINER_PORT="${REC_PORT:-8789}"
MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 'TU_IP_MAC')"

cat <<EOF
=== Flash firmware de captura — Satellite1 ===

1. Arranca el trainer UI (si no está corriendo):
   ./infrastructure/voice/wake-word/setup_trainer_macos.sh ui

2. Abre http://127.0.0.1:${TRAINER_PORT} → pestaña **Firmware**

3. Selecciona:
   - Device type: Satellite1
   - OTA target: ${SAT_IP} (o descubrir por mDNS)

4. Flash OTA del firmware Tater de captura

5. En Home Assistant → Dispositivos → Satellite1, configura:
   - Capture Wake Audio: ON
   - Capture Close Misses: ON
   - Trainer App URL: http://${MAC_IP}:${TRAINER_PORT}

6. Recoge muestras:
   - Di "Mariano" varias veces (positivas)
   - Deja TV encendida y marca falsos despertares como "False wake"

7. Pestaña Captured Audio → aprobar/rechazar clips

8. Re-entrenar: Trainer → Start training

9. Tras entrenar: copy_model_from_trainer.sh → serve_model.sh → flash firmware final

EOF

if ping -c 1 -W 2 "$SAT_IP" >/dev/null 2>&1; then
  echo "✅ Satellite1 responde en $SAT_IP"
else
  echo "⚠️  Satellite1 no responde en $SAT_IP — conecta a la red del homelab"
fi
