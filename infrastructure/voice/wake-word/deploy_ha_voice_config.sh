#!/usr/bin/env bash
# deploy_ha_voice_config.sh — Despliega config HA de voz a /config/
#
# Uso:
#   HA_HOST=192.168.1.110 HA_USER=root ./deploy_ha_voice_config.sh
#
# Requiere acceso SSH al HAOS. Ajusta rutas si usas Samba/Studio Code Server.
#
# Layout (igual que deploy_speaker_id_ha_config.sh):
#   /config/configuration.yaml            ← home-assistant/configuration.haos.yaml
#   /config/includes/*.yaml               ← home-assistant/includes/*.yaml
#   /config/custom_sentences/es/*.yaml    ← home-assistant/custom_sentences/es/*.yaml
#   /config/secrets.yaml                  ← no se toca
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/config}"

# Mantener sincronizado con configuration.haos.yaml y deploy_speaker_id_ha_config.sh
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

SENTENCES_SRC="$REPO_ROOT/home-assistant/custom_sentences/es"

log() { printf '[deploy-ha-voice] %s\n' "$*"; }

if ! ping -c 1 -W 2 "$HA_HOST" >/dev/null 2>&1; then
  log "❌ No hay respuesta de $HA_HOST — conecta a la red del homelab"
  exit 1
fi

log "Desplegando a ${HA_USER}@${HA_HOST}:${HA_CONFIG}"

ssh "${HA_USER}@${HA_HOST}" \
  "mkdir -p ${HA_CONFIG}/includes ${HA_CONFIG}/themes ${HA_CONFIG}/custom_sentences/es"

scp "$REPO_ROOT/home-assistant/configuration.haos.yaml" \
  "${HA_USER}@${HA_HOST}:${HA_CONFIG}/configuration.yaml"

for f in "${INCLUDE_FILES[@]}"; do
  src="$REPO_ROOT/home-assistant/includes/${f}"
  if [[ ! -f "$src" ]]; then
    log "❌ Falta ${src}"
    exit 1
  fi
  log "Copiando includes/${f}..."
  scp "$src" "${HA_USER}@${HA_HOST}:${HA_CONFIG}/includes/${f}"
done

shopt -s nullglob
sentence_files=("$SENTENCES_SRC"/*.yaml)
if [[ ${#sentence_files[@]} -eq 0 ]]; then
  log "❌ No hay custom_sentences en ${SENTENCES_SRC}"
  exit 1
fi
for src in "${sentence_files[@]}"; do
  log "Copiando custom_sentences/es/$(basename "$src")..."
  scp "$src" "${HA_USER}@${HA_HOST}:${HA_CONFIG}/custom_sentences/es/$(basename "$src")"
done

log "Validando configuración (ha core check)..."
ssh "${HA_USER}@${HA_HOST}" "ha core check"

# El CLI de HAOS no tiene subcomando reload. Copiar YAML no carga
# automatizaciones: hace falta restart de Core (o recarga YAML en la UI).
if [[ "${HA_SKIP_RESTART:-0}" == "1" ]]; then
  log "HA_SKIP_RESTART=1 — no se reinicia Core. Recarga YAML a mano:"
  log "  Herramientas de desarrollo → YAML → Automatizaciones"
else
  log "Reiniciando Home Assistant Core para cargar automations..."
  ssh "${HA_USER}@${HA_HOST}" "ha core restart"
fi

log "✅ Despliegue completado"
log "Verifica: Configuración → Automatizaciones → Satellite1 — sensibilidad wake word según TV"
log "Frases Assist: Herramientas de desarrollo → YAML → Recargar frases de conversación"
log "NLU registry (área/aliases/exponer): ./configure_ha_voice_nlu.sh --apply"
log "secrets.yaml no se ha modificado"
