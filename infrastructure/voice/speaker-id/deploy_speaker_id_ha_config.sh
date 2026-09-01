#!/usr/bin/env bash
# deploy_speaker_id_ha_config.sh — Despliega config HA para speaker ID + folder watcher
#
# Uso:
#   HA_HOST=192.168.1.110 HA_USER=root ./deploy_speaker_id_ha_config.sh
#
# Requiere SSH a HAOS. Crea backup en /config/backups/ antes de modificar.
#
# Layout desplegado (alineado con home-assistant/includes/ del repo):
#   /config/configuration.yaml   ← home-assistant/configuration.haos.yaml
#   /config/includes/*.yaml      ← home-assistant/includes/*.yaml (subcarpeta)
#   /config/themes/*.yaml        ← home-assistant/themes/*.yaml

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/config}"
TS="$(date +%Y%m%d-%H%M%S)"
FOLDER_WATCHER_ENTRY_ID="01JUN23WAYNESPKRASSISTPIPE"

# Includes desplegados 1:1 desde home-assistant/includes/ a /config/includes/.
# Mantener esta lista sincronizada con configuration.haos.yaml.
INCLUDE_FILES=(
  automations.yaml
  scripts.yaml
  scenes.yaml
  sensors.yaml
  input_text.yaml
  input_boolean.yaml
  lights.yaml
  rest_commands.yaml
  shell_commands.yaml
  intent_scripts.yaml
)

log() { printf '[deploy-speaker-id-ha] %s\n' "$*"; }

if ! ping -c 1 -W 2 "$HA_HOST" >/dev/null 2>&1; then
  log "❌ No hay respuesta de $HA_HOST"
  exit 1
fi

log "Backup y despliegue → ${HA_USER}@${HA_HOST}:${HA_CONFIG}"

ssh "${HA_USER}@${HA_HOST}" "mkdir -p ${HA_CONFIG}/backups ${HA_CONFIG}/includes ${HA_CONFIG}/themes /share/assist_pipeline"

ssh "${HA_USER}@${HA_HOST}" "
  cp -a ${HA_CONFIG}/configuration.yaml ${HA_CONFIG}/backups/configuration.yaml.${TS} 2>/dev/null || true
  cp -a ${HA_CONFIG}/includes ${HA_CONFIG}/backups/includes.${TS} 2>/dev/null || true
  cp -a ${HA_CONFIG}/.storage/core.config_entries ${HA_CONFIG}/backups/core.config_entries.${TS} 2>/dev/null || true
"

scp "${REPO_ROOT}/home-assistant/configuration.haos.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/configuration.yaml"

for f in "${INCLUDE_FILES[@]}"; do
  src="${REPO_ROOT}/home-assistant/includes/${f}"
  if [[ ! -f "$src" ]]; then
    log "❌ Falta ${src}"
    exit 1
  fi
  log "Copiando includes/${f}..."
  scp "$src" "${HA_USER}@${HA_HOST}:${HA_CONFIG}/includes/${f}"
done

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
