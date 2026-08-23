#!/usr/bin/env bash
# teardown_runpod_trainer.sh — Descarga el modelo, para el GPU Pod y (opt-in) borra el volume
#
# Orden fijo: receive/scp → verificar tflite+json locales → pod stop →
# network-volume delete solo con --delete-volume.
# Vive en el PC. No borra el volume desde el pod (riesgo de perder el modelo).
# Ejecutable con bash (Git Bash) o zsh (macOS Tahoe): zsh ./teardown_runpod_trainer.sh

set -euo pipefail

# bash: BASH_SOURCE; zsh (macOS): $0 — no tocar BASH_SOURCE bajo zsh + set -u
_this="$0"
if [ -n "${BASH_VERSION:-}" ]; then
  _this="${BASH_SOURCE[0]}"
fi
SCRIPT_DIR="$(cd "$(dirname "$_this")" && pwd)"
POD_ID="${MWW_RUNPOD_POD_ID:-POD_ID}"
VOLUME_ID="${MWW_RUNPOD_VOLUME_ID:-}"
DATA_DIR="${MWW_RUNPOD_DATA_DIR:-$HOME/mww-runpod}"
WAKE_WORD="${MWW_WAKE_WORD:-mariano}"
SSH_CMD="${MWW_RUNPOD_SSH:-}"
POLL_S="${MWW_TEARDOWN_POLL_S:-60}"
WATCH_MAX_S="${MWW_TEARDOWN_WATCH_MAX_S:-172800}"
REMOTE_DIR="/data/trained_wake_words"
DEST="$DATA_DIR/trained_wake_words"
DRY_RUN=0
DELETE_VOLUME=0
WATCH=0

log() { printf '[teardown-runpod] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--dry-run] [--delete-volume] [--watch] [--help]

Tras el train: descarga ${WAKE_WORD}.{tflite,json}, verifica, para el GPU Pod.
El network volume NO se borra salvo --delete-volume (destructivo).

  --dry-run         Imprime receive / pod stop / delete sin ejecutar
  --delete-volume   Tras verificar, runpodctl network-volume delete (exige MWW_RUNPOD_VOLUME_ID)
  --watch           Espera artefactos (intervalo ${POLL_S}s, tope ${WATCH_MAX_S}s)
  --help            Esta ayuda

Variables:
  MWW_RUNPOD_POD_ID=$POD_ID
  MWW_RUNPOD_VOLUME_ID=${VOLUME_ID:-"(vacio)"}
  MWW_RUNPOD_DATA_DIR=$DATA_DIR
  MWW_WAKE_WORD=$WAKE_WORD
  MWW_RUNPOD_SSH            # opcional: comando SSH para --watch / scp
  MWW_TEARDOWN_POLL_S=$POLL_S
  MWW_TEARDOWN_WATCH_MAX_S=$WATCH_MAX_S

Orden: receive o scp → verificar → runpodctl pod stop → (opt-in) network-volume delete
Luego: MWW_RUNPOD_DATA_DIR=$DATA_DIR $SCRIPT_DIR/copy_model_from_trainer.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY_RUN=1; shift ;;
    --delete-volume)  DELETE_VOLUME=1; shift ;;
    --watch)          WATCH=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    *)                die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

TFLITE="$DEST/${WAKE_WORD}.tflite"
JSON="$DEST/${WAKE_WORD}.json"

artifacts_ok() {
  [[ -f "$TFLITE" && -s "$TFLITE" && -f "$JSON" ]]
}

print_receive_help() {
  cat <<EOF
--- Descargar artefactos (antes de parar el pod) ---
En el pod:
  runpodctl send ${REMOTE_DIR}/${WAKE_WORD}.tflite ${REMOTE_DIR}/${WAKE_WORD}.json
En este PC:
  mkdir -p ${DEST}
  runpodctl receive
  # mueve ${WAKE_WORD}.{tflite,json} a ${DEST}
scp (si MWW_RUNPOD_SSH está definido):
  scp ...:${REMOTE_DIR}/${WAKE_WORD}.tflite ${DEST}/
  scp ...:${REMOTE_DIR}/${WAKE_WORD}.json ${DEST}/
EOF
}

require_volume_id() {
  if [[ "$DELETE_VOLUME" -eq 1 && -z "$VOLUME_ID" ]]; then
    die "MWW_RUNPOD_VOLUME_ID es obligatorio con --delete-volume"
  fi
}

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry-run: no se llama a RunPod"
  log "DEST=$DEST  POD_ID=$POD_ID  remote=$REMOTE_DIR"
  if [[ "$WATCH" -eq 1 ]]; then
    log "--watch: espera artefactos (intervalo ${POLL_S}s, tope ${WATCH_MAX_S}s)"
    if [[ -n "$SSH_CMD" ]]; then
      log "SSH: $SSH_CMD test -s ${REMOTE_DIR}/${WAKE_WORD}.tflite"
    else
      log "Sin MWW_RUNPOD_SSH: --watch espera ficheros locales en $DEST"
    fi
  fi
  print_receive_help
  log "Verificar: $TFLITE (tamaño > 0) y $JSON"
  log "Siguiente si OK: runpodctl pod stop ${POD_ID}"
  if [[ "$DELETE_VOLUME" -eq 1 ]]; then
    if [[ -z "$VOLUME_ID" ]]; then
      log "ERROR: --delete-volume exige MWW_RUNPOD_VOLUME_ID"
    else
      log "runpodctl network-volume delete ${VOLUME_ID}"
    fi
  else
    log "Volume: no se borra (pasa --delete-volume + MWW_RUNPOD_VOLUME_ID)"
  fi
  log "Copia al repo: MWW_RUNPOD_DATA_DIR=$DATA_DIR $SCRIPT_DIR/copy_model_from_trainer.sh"
  exit 0
fi

require_volume_id

if [[ "$POD_ID" == "POD_ID" || -z "$POD_ID" ]]; then
  die "Define MWW_RUNPOD_POD_ID (id real del pod)"
fi

mkdir -p "$DEST"

watch_for_artifacts() {
  local elapsed=0
  log "--watch: espera artefactos (intervalo ${POLL_S}s, tope ${WATCH_MAX_S}s)"
  while ! artifacts_ok; do
    if [[ -n "$SSH_CMD" ]]; then
      if $SSH_CMD "test -s ${REMOTE_DIR}/${WAKE_WORD}.tflite && test -f ${REMOTE_DIR}/${WAKE_WORD}.json"; then
        log "Artefactos remotos listos — descarga con receive/scp"
        break
      fi
    fi
    if [[ "$elapsed" -ge "$WATCH_MAX_S" ]]; then
      die "Timeout --watch (${WATCH_MAX_S}s): faltan artefactos ${WAKE_WORD}.tflite/.json"
    fi
    log "Aún no hay artefactos; reintento en ${POLL_S}s"
    sleep "$POLL_S"
    elapsed=$((elapsed + POLL_S))
  done
}

if [[ "$WATCH" -eq 1 ]]; then
  watch_for_artifacts
fi

if ! artifacts_ok; then
  print_receive_help
  die "Faltan artefactos locales ${WAKE_WORD}.tflite/.json en $DEST — no se para el pod ni se borra el volume"
fi

if ! command -v runpodctl >/dev/null 2>&1; then
  die "runpodctl no está en PATH. Instálalo o para el pod a mano en la consola."
fi

log "Artefactos OK — runpodctl pod stop $POD_ID"
runpodctl pod stop "$POD_ID"

if [[ "$DELETE_VOLUME" -eq 1 ]]; then
  log "runpodctl network-volume delete $VOLUME_ID"
  runpodctl network-volume delete "$VOLUME_ID"
fi

log "Copia al repo: MWW_RUNPOD_DATA_DIR=$DATA_DIR $SCRIPT_DIR/copy_model_from_trainer.sh"
