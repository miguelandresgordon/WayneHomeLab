#!/usr/bin/env bash
# configure_ha_voice_nlu.sh — Área Salón, aliases y exposición Assist
#
# El registry vive en HAOS (.storage), no en YAML. Este script:
#   1. Imprime el checklist de UI (siempre)
#   2. Con --dry-run, lee el registry por SSH y muestra el diff
#   3. Con --apply, para Core, parchea entity_registry con jq y arranca
#
# Uso:
#   ./configure_ha_voice_nlu.sh
#   ./configure_ha_voice_nlu.sh --dry-run
#   ./configure_ha_voice_nlu.sh --apply
#
# SSH: HA_SSH (host de ~/.ssh/config, default homeassistant) o HA_USER@HA_HOST
set -euo pipefail

HA_SSH="${HA_SSH:-homeassistant}"
HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/config}"
REGISTRY="${HA_CONFIG}/.storage/core.entity_registry"
AREA_ID="salon"
LAMP_ENTITY="light.yeelink_mono6_6409_light"

MODE="checklist"
for arg in "$@"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --apply) MODE="apply" ;;
    -h|--help)
      cat <<'EOF'
Uso: configure_ha_voice_nlu.sh [--dry-run|--apply]

Configura NLU de voz: área Salón, aliases de la lámpara y exposición Assist.

  (sin flags)  Checklist de UI + entidades objetivo
  --dry-run    Lee el registry en HAOS y muestra qué cambiaría
  --apply      ha core stop → jq patch → ha core start (corta voz ~30 s)

Variables: HA_SSH (default homeassistant), o HA_USER + HA_HOST
EOF
      exit 0
      ;;
    *)
      printf 'Flag desconocido: %s (usa --help)\n' "$arg" >&2
      exit 1
      ;;
  esac
done

log() { printf '[configure-ha-voice-nlu] %s\n' "$*"; }

EXPOSE_ON=(
  light.yeelink_mono6_6409_light
  media_player.tv_ga_2
  script.pon_la_radio
  script.apagar_tele
  script.encender_tele
)

EXPOSE_OFF=(
  scene.lampara_apagada
  scene.cine
  scene.lectura
  scene.relajado
  light.luz_habitacion
  light.dormitorio_luz_habitacion
  light.salon_lampara_tuya
  light.todas_las_luces
  media_player.tv_ga
  media_player.bravia_4k_gb_atv3
  media_player.bravia_4k_gb_atv3_2
  media_player.bravia_4k_gb_atv3_3
  media_player.macbook_pro_de_alicia
  media_player.mandresg_macpro
  media_player.satellite1
  media_player.satellite1_c7ffe4_media_player
)

print_checklist() {
  cat <<EOF
=== NLU Assist — checklist (Salón / lámpara Xiaomi) ===

1. Área
   Ajustes → Áreas → Salón (id: ${AREA_ID})
   Asignar ${LAMP_ENTITY} al área Salón

2. Aliases de la lámpara (Ajustes → Entidades → Lámpara → Aliases de voz)
   lámpara, lampara, luz del salón, luz

3. Exponer a Assist (Ajustes → Asistentes de voz → Exponer)
   ON:  ${LAMP_ENTITY}, media_player.tv_ga_2,
        script.{pon_la_radio,apagar_tele,encender_tele}
   OFF: escena Salón off (scene.lampara_apagada), resto de escenas,
        light.luz_habitacion / dormitorio / salon_lampara_tuya / todas_las_luces,
        media_player.tv_ga, Bravia extra, Macs, media_player del satélite

4. Escena
   YAML name = «Salón off» (ya no «Lámpara apagada»). No exponer.

5. Tras YAML deploy
   Herramientas de desarrollo → YAML → Recargar frases de conversación
   Probar: «enciende la lámpara» → solo light.yeelink_mono6_6409_light

SSH apply: $0 --apply   (para Core ~30 s)
EOF
}

_SSH_TARGET=""
ssh_target() {
  if [[ -n "$_SSH_TARGET" ]]; then
    printf '%s\n' "$_SSH_TARGET"
    return
  fi
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$HA_SSH" true 2>/dev/null; then
    _SSH_TARGET="$HA_SSH"
  else
    _SSH_TARGET="${HA_USER}@${HA_HOST}"
  fi
  printf '%s\n' "$_SSH_TARGET"
}

ssh_ha() {
  ssh -o BatchMode=yes "$(ssh_target)" "$@"
}

jq_program() {
  # Args passed as $expose_on_json $expose_off_json
  cat <<'JQ'
def set_expose($on):
  .options = ((.options // {}) + {conversation: ((.options.conversation // {}) + {should_expose: $on})});

.data.entities |= map(
  if .entity_id == $lamp then
    .area_id = $area
    | .aliases = ["lámpara", "lampara", "luz del salón", "luz"]
    | set_expose(true)
  else . end
  | if (.entity_id as $e | $expose_on | index($e)) then set_expose(true) else . end
  | if (.entity_id as $e | $expose_off | index($e)) then set_expose(false) else . end
)
JQ
}

print_checklist

if [[ "$MODE" == "checklist" ]]; then
  exit 0
fi

if ! ssh_ha true >/dev/null; then
  log "❌ SSH a HAOS no disponible — usa el checklist de UI"
  exit 1
fi

expose_on_json=$(printf '%s\n' "${EXPOSE_ON[@]}" | jq -R . | jq -s .)
expose_off_json=$(printf '%s\n' "${EXPOSE_OFF[@]}" | jq -R . | jq -s .)

read_report() {
  ssh_ha "jq -r --arg lamp '$LAMP_ENTITY' '
    .data.entities[]
    | select(.entity_id == \$lamp
        or (.options.conversation.should_expose == true)
        or (.entity_id | startswith(\"scene.\"))
        or (.entity_id | startswith(\"light.\"))
        or (.entity_id | startswith(\"media_player.\")))
    | [.entity_id, (.area_id // \"\"), ((.aliases // []) | join(\",\")), ((.options.conversation.should_expose // false) | tostring)]
    | @tsv
  ' '$REGISTRY'"
}

log "Estado actual (entity_id / area / aliases / exposed):"
read_report || log "⚠️  No se pudo leer $REGISTRY"

if [[ "$MODE" == "dry-run" ]]; then
  log "Dry-run: no se escribe. Área objetivo=${AREA_ID} aliases=lámpara,lampara,luz del salón,luz"
  log "Expose ON:  ${EXPOSE_ON[*]}"
  log "Expose OFF: ${EXPOSE_OFF[*]}"
  exit 0
fi

log "Aplicando: ha core stop → patch → ha core start"
jq_file="$(mktemp)"
trap 'rm -f "$jq_file"' EXIT
jq_program >"$jq_file"
scp -o BatchMode=yes "$jq_file" "$(ssh_target):/tmp/configure_ha_voice_nlu.jq"
ssh_ha "ha core stop"
ssh_ha "cp -a '$REGISTRY' '${REGISTRY}.bak.voice-nlu' && jq --arg lamp '$LAMP_ENTITY' --arg area '$AREA_ID' --argjson expose_on '$expose_on_json' --argjson expose_off '$expose_off_json' -f /tmp/configure_ha_voice_nlu.jq '$REGISTRY' > '${REGISTRY}.tmp' && mv '${REGISTRY}.tmp' '$REGISTRY' && rm -f /tmp/configure_ha_voice_nlu.jq"
ssh_ha "ha core start"

log "✅ Registry actualizado. Verifica en UI: lámpara en Salón, escena Salón off no expuesta."
log "Backup: ${REGISTRY}.bak.voice-nlu"
