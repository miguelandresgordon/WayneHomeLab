#!/usr/bin/env bash
# deploy_speaker_id_ha_config.sh — Despliega config HA para speaker ID + folder watcher
#
# Uso:
#   HA_HOST=192.168.1.110 HA_USER=root ./deploy_speaker_id_ha_config.sh
#
# Requiere SSH a HAOS. Crea backup en /config/backups/ antes de modificar.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/config}"
TS="$(date +%Y%m%d-%H%M%S)"
FOLDER_WATCHER_ENTRY_ID="01JUN23WAYNESPKRASSISTPIPE"

log() { printf '[deploy-speaker-id-ha] %s\n' "$*"; }

if ! ping -c 1 -W 2 "$HA_HOST" >/dev/null 2>&1; then
  log "❌ No hay respuesta de $HA_HOST"
  exit 1
fi

log "Backup y despliegue → ${HA_USER}@${HA_HOST}:${HA_CONFIG}"

ssh "${HA_USER}@${HA_HOST}" "mkdir -p ${HA_CONFIG}/backups ${HA_CONFIG}/includes /share/assist_pipeline"

ssh "${HA_USER}@${HA_HOST}" "
  cp -a ${HA_CONFIG}/configuration.yaml ${HA_CONFIG}/backups/configuration.yaml.${TS} 2>/dev/null || true
  cp -a ${HA_CONFIG}/automations.yaml ${HA_CONFIG}/backups/automations.yaml.${TS} 2>/dev/null || true
  cp -a ${HA_CONFIG}/.storage/core.config_entries ${HA_CONFIG}/backups/core.config_entries.${TS} 2>/dev/null || true
"

ssh "${HA_USER}@${HA_HOST}" "mkdir -p ${HA_CONFIG}/themes"

scp "${REPO_ROOT}/home-assistant/configuration.haos.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/configuration.yaml"

scp "${REPO_ROOT}/home-assistant/includes/automations.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/automations.yaml"

scp "${REPO_ROOT}/home-assistant/includes/scripts.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/scripts.yaml"

scp "${REPO_ROOT}/home-assistant/includes/scenes.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/scenes.yaml"

scp "${REPO_ROOT}/home-assistant/includes/input_boolean.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/input_boolean.yaml"

scp "${REPO_ROOT}/home-assistant/includes/lights.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/lights.yaml"

scp "${REPO_ROOT}/home-assistant/includes/input_text.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/input_text.yaml"

scp "${REPO_ROOT}/home-assistant/includes/rest_commands.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/rest_commands.yaml"

scp "${REPO_ROOT}/home-assistant/includes/shell_commands.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/shell_commands.yaml"

scp "${REPO_ROOT}/home-assistant/themes/wayne_default.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/themes/wayne_default.yaml"

log "Registrando integración Folder Watcher (config entry)..."
ssh "${HA_USER}@${HA_HOST}" bash -s <<EOF
set -euo pipefail
CFG="${HA_CONFIG}/.storage/core.config_entries"
if jq -e '.data.entries[] | select(.domain=="folder_watcher" and .options.folder=="/share/assist_pipeline")' "\$CFG" >/dev/null 2>&1; then
  echo "Folder Watcher ya configurado para /share/assist_pipeline"
else
  NOW=\$(date -u +"%Y-%m-%dT%H:%M:%S.000000+00:00")
  TMP=\$(mktemp)
  jq --arg now "\$NOW" --arg id "${FOLDER_WATCHER_ENTRY_ID}" '
    .data.entries += [{
      "created_at": \$now,
      "data": {},
      "disabled_by": null,
      "discovery_keys": {},
      "domain": "folder_watcher",
      "entry_id": \$id,
      "minor_version": 1,
      "modified_at": \$now,
      "options": {"folder": "/share/assist_pipeline", "patterns": ["*.wav"]},
      "pref_disable_new_entities": false,
      "pref_disable_polling": false,
      "source": "user",
      "subentries": [],
      "title": "Folder Watcher /share/assist_pipeline",
      "unique_id": null,
      "version": 1
    }]
  ' "\$CFG" > "\$TMP" && mv "\$TMP" "\$CFG"
  echo "Folder Watcher añadido"
fi
EOF

log "Ajustando umbral de la app al valor exportado (0.7322)..."
ssh "${HA_USER}@${HA_HOST}" "ha apps options local_speaker_id_mariano \
  --option threshold=0.7322 2>/dev/null || true"

log "Validando configuración..."
if ssh "${HA_USER}@${HA_HOST}" "ha core check" 2>&1; then
  log "Reiniciando Home Assistant Core..."
  ssh "${HA_USER}@${HA_HOST}" "ha core restart"
else
  log "⚠️  ha core check falló — revisa logs antes de reiniciar"
  exit 1
fi

log "✅ Despliegue completado"
log "Prueba: copia un WAV a /share/assist_pipeline/ y revisa input_text.current_speaker"
