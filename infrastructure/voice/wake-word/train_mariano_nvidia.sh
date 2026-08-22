#!/usr/bin/env bash
# train_mariano_nvidia.sh — Arranca/sincroniza el trainer Docker para "mariano"
#
# El trainer Tater es UI-first (http://127.0.0.1:8789). Este script
# sincroniza personal_samples, asegura el contenedor y deja instrucciones
# para Start training con wake word=mariano e idioma Spanish.
#
# AMD Radeon RX 6750 XT: pasa --cpu (omite --gpus all). CUDA no aplica.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${MWW_NVIDIA_DATA_DIR:-$HOME/mww-data}"
CONTAINER_NAME="${MWW_NVIDIA_CONTAINER:-waynelab-mww-trainer}"
WAKE_WORD="${MWW_WAKE_WORD:-mariano}"
REC_PORT="${REC_PORT:-8789}"
DRY_RUN=0
CPU=0

log() { printf '[train-mariano-nvidia] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--cpu] [--dry-run] [--help]

Sincroniza personal_samples a \$MWW_NVIDIA_DATA_DIR y deja el contenedor
listo para entrenar la wake word ${WAKE_WORD} en la UI :${REC_PORT}.

  --cpu       AMD / sin NVIDIA: pasa --cpu a setup_trainer_nvidia.sh
  --dry-run   No toca docker; imprime los pasos
  --help      Esta ayuda

Variables:
  MWW_NVIDIA_DATA_DIR=$DATA_DIR
  MWW_NVIDIA_CONTAINER=$CONTAINER_NAME
  MWW_WAKE_WORD=$WAKE_WORD
  REC_PORT=$REC_PORT
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cpu) CPU=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

sync_samples() {
  local src dest count
  dest="$DATA_DIR/personal_samples"
  mkdir -p "$dest"
  for src in \
    "${MWW_PERSONAL_SRC:-}" \
    "$SCRIPT_DIR/personal_samples" \
    "${WAKEWORD_TRAINER_DATA_DIR:-$HOME/.taterwakewordtrainer/app/current}/personal_samples"
  do
    [[ -n "$src" && -d "$src" ]] || continue
    count="$(find "$src" -maxdepth 1 -type f \( -name '*.wav' -o -name '*.WAV' \) 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "${count:-0}" -gt 0 ]]; then
      log "Sincronizando $count WAV → $dest"
      if [[ "$DRY_RUN" -eq 0 ]]; then
        "$SCRIPT_DIR/export_personal_samples.sh" --src "$src" --dest "$dest"
      fi
      return 0
    fi
  done
  log "Sin WAV de personal_samples que copiar (puedes subirlos en la UI Samples)"
}

log "Wake word=$WAKE_WORD UI=http://127.0.0.1:${REC_PORT}"
log "DATA_DIR=$DATA_DIR"
if [[ "$CPU" -eq 1 ]]; then
  log "Modo CPU (AMD Radeon / CUDA no aplica)"
fi
sync_samples

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry-run: docker start $CONTAINER_NAME  # o setup_trainer_nvidia.sh$( [[ "$CPU" -eq 1 ]] && printf ' --cpu' )"
  log "Siguiente: abre http://127.0.0.1:${REC_PORT} → Trainer → ${WAKE_WORD} / Spanish → Start training"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  die "docker no está en PATH. Ejecuta primero setup_trainer_nvidia.sh (o setup_trainer_windows.ps1)"
fi

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker start "$CONTAINER_NAME" >/dev/null
  log "Contenedor $CONTAINER_NAME en marcha"
else
  log "Contenedor ausente — lanzando setup_trainer_nvidia.sh"
  if [[ "$CPU" -eq 1 ]]; then
    "$SCRIPT_DIR/setup_trainer_nvidia.sh" --cpu
  else
    "$SCRIPT_DIR/setup_trainer_nvidia.sh"
  fi
fi

log "Abre http://127.0.0.1:${REC_PORT}"
log "Trainer → wake word=${WAKE_WORD} → language=Spanish → confirma personal_samples → Start training"
log "Artefactos: $DATA_DIR/trained_wake_words/${WAKE_WORD}.{tflite,json}"
log "Copia al repo: WAKEWORD_TRAINER_DATA_DIR=$DATA_DIR $SCRIPT_DIR/copy_model_from_trainer.sh"
