#!/usr/bin/env bash
# deploy_ha_voice_config.sh — Despliega config HA de voz (automations + configuration)
#
# Uso:
#   HA_HOST=192.168.1.110 HA_USER=root ./deploy_ha_voice_config.sh
#
# Requiere acceso SSH al HAOS. Ajusta rutas si usas Samba/Studio Code Server.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/config}"

log() { printf '[deploy-ha-voice] %s\n' "$*"; }

if ! ping -c 1 -W 2 "$HA_HOST" >/dev/null 2>&1; then
  log "❌ No hay respuesta de $HA_HOST — conecta a la red del homelab"
  exit 1
fi

log "Desplegando a ${HA_USER}@${HA_HOST}:${HA_CONFIG}"

scp "$REPO_ROOT/home-assistant/configuration.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/configuration.yaml"

scp "$REPO_ROOT/home-assistant/includes/automations.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/includes/automations.yaml"

log "Recargando automations y core config..."
ssh "${HA_USER}@${HA_HOST}" "ha core reload" 2>/dev/null || \
  ssh "${HA_USER}@${HA_HOST}" "curl -s -X POST -H 'Authorization: Bearer ${HA_TOKEN:-}' \
    http://127.0.0.1:8123/api/services/automation/reload" 2>/dev/null || \
  log "⚠️  Recarga manual: Configuración → Sistema → Reiniciar (o Developer Tools → YAML reload)"

log "✅ Despliegue completado"
log "Verifica: Configuración → Comprobar configuración"
