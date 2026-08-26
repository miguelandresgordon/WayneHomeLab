#!/usr/bin/env bash
# deploy_to_haos.sh — Copia artefactos speaker-id a HAOS /share/speaker-id/
#
# Uso:
#   ./infrastructure/voice/speaker-id/deploy_to_haos.sh
#   HA_HOST=192.168.1.110 ./infrastructure/voice/speaker-id/deploy_to_haos.sh
#
# Requiere: SSH al HAOS (complemento Terminal & SSH activo, clave en root@HA_HOST)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORT_DIR="${EXPORT_DIR:-${SCRIPT_DIR}/export}"
HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/share/speaker-id}"

log() { printf '[deploy-speaker-id] %s\n' "$*"; }

required_files=(
  "${EXPORT_DIR}/speaker_profiles.json"
  "${EXPORT_DIR}/config.json"
  "${EXPORT_DIR}/wespeaker_en_voxceleb_resnet34.onnx"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "${file}" ]]; then
    log "ERROR: falta ${file}"
    log "Genera primero: python3 ${SCRIPT_DIR}/train_profiles.py"
    exit 1
  fi
done

if ! ping -c 1 -W 3 "${HA_HOST}" >/dev/null 2>&1; then
  log "ERROR: ${HA_HOST} no responde (ping)"
  log "Arranca la VM HAOS: ssh -t pi@192.168.1.100 'sudo qm start 100'"
  exit 1
fi

if ! nc -z -w 3 "${HA_HOST}" 22 2>/dev/null; then
  log "ERROR: SSH (puerto 22) cerrado en ${HA_HOST}"
  log ""
  log "El complemento Terminal & SSH suele estar 'iniciado' pero SIN puerto de red."
  log "Habilita SSH en la pestaña Configuración del complemento:"
  log "  1. http://${HA_HOST}:8123 → Ajustes → Complementos → Terminal & SSH"
  log "  2. Pestaña Configuración → sección Red / Network"
  log "  3. Pulsa 'Mostrar puertos deshabilitados' (Show disabled ports)"
  log "  4. En la fila SSH, columna Host, escribe: 22"
  log "  5. Guardar → Reiniciar complemento"
  log "  6. Pestaña Registro: debe aparecer 'SSH ... listening on port 22'"
  log ""
  log "También necesitas clave pública O contraseña en la configuración."
  log "Comprueba: nc -zv ${HA_HOST} 22"
  log ""
  log "Alternativa: complemento Samba → copia manual a /share/speaker-id/"
  exit 1
fi

log "Creando ${REMOTE_DIR} en ${HA_USER}@${HA_HOST}..."
ssh "${HA_USER}@${HA_HOST}" "mkdir -p '${REMOTE_DIR}'"

log "Copiando artefactos (~50 MB)..."
scp "${required_files[@]}" "${HA_USER}@${HA_HOST}:${REMOTE_DIR}/"

# ZIP opcional (referencia)
if [[ -f "${EXPORT_DIR}/speaker-id-mariano-export.zip" ]]; then
  scp "${EXPORT_DIR}/speaker-id-mariano-export.zip" "${HA_USER}@${HA_HOST}:${REMOTE_DIR}/"
fi

log "Verificando en remoto..."
ssh "${HA_USER}@${HA_HOST}" "ls -lh '${REMOTE_DIR}/'"

log "Listo. Siguiente: instala/arranca add-on speaker-id-mariano y prueba:"
log "  curl http://${HA_HOST}:10400/health"
