#!/usr/bin/env bash
# setup_trainer_nvidia.sh — Prepara microWakeWord-Trainer (Docker; GPU NVIDIA o CPU)
#
# Windows 11 + NVIDIA: Docker Desktop (WSL2) + --gpus all.
# Windows 11 + AMD (RX 6750 XT): la misma imagen SIN --gpus all (--cpu).
# TensorFlow CUDA nativo en Windows no es fiable; el contenedor Linux sí lo es.
#
# Uso:
#   ./setup_trainer_nvidia.sh                 # pull + crear data dir + docker run (GPU)
#   ./setup_trainer_nvidia.sh --cpu           # AMD / sin NVIDIA: omite --gpus all
#   ./setup_trainer_nvidia.sh --dry-run       # imprime comandos, no ejecuta docker
#   ./setup_trainer_nvidia.sh --blackwell     # imagen RTX 50-series
#   MWW_NVIDIA_DATA_DIR=/data/mww ./setup_trainer_nvidia.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${MWW_NVIDIA_DATA_DIR:-$HOME/mww-data}"
CONTAINER_NAME="${MWW_NVIDIA_CONTAINER:-waynelab-mww-trainer}"
IMAGE_LATEST="ghcr.io/tatertotterson/microwakeword:latest"
IMAGE_BLACKWELL="ghcr.io/tatertotterson/microwakeword:blackwell"
IMAGE="$IMAGE_LATEST"
REC_PORT="${REC_PORT:-8789}"
DRY_RUN=0
BLACKWELL=0
CPU=0

log() { printf '[setup-trainer-nvidia] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--cpu] [--dry-run] [--blackwell] [--help]

  --cpu         Omite --gpus all (AMD Radeon RX 6750 XT / sin NVIDIA)
  --dry-run     Imprime docker pull/run sin ejecutarlos
  --blackwell   Usa la imagen CUDA 12.8 para RTX 50-series (sm_120)
  --help        Esta ayuda

Variables:
  MWW_NVIDIA_DATA_DIR=$DATA_DIR     # se monta en /data (personal_samples, TTS, modelo)
  MWW_NVIDIA_CONTAINER=$CONTAINER_NAME
  MWW_PERSONAL_SRC                  # opcional: WAV a copiar a personal_samples/
  REC_PORT=$REC_PORT

Requisitos: Docker, ≥ 80 GB libres (primera vez; TTS+negativos).
En Windows 11 usa Docker Desktop + WSL2, no TensorFlow nativo.
RX 6750 XT: CUDA no aplica — usa --cpu.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cpu)        CPU=1; shift ;;
    --dry-run)    DRY_RUN=1; shift ;;
    --blackwell)  BLACKWELL=1; IMAGE="$IMAGE_BLACKWELL"; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

if [[ "$BLACKWELL" -eq 1 && "$CPU" -eq 1 ]]; then
  die "--blackwell requiere GPU NVIDIA; no lo combines con --cpu"
fi

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    log "Ejecutando: $*"
    "$@"
  fi
}

if [[ "$BLACKWELL" -eq 1 ]]; then
  log "Imagen Blackwell (RTX 50-series): $IMAGE"
elif [[ "$CPU" -eq 1 ]]; then
  log "Modo CPU: $IMAGE (sin --gpus all; AMD Radeon / CUDA no aplica)"
else
  log "Imagen CUDA estándar: $IMAGE"
fi

log "DATA_DIR=$DATA_DIR (personal_samples irán a $DATA_DIR/personal_samples)"
if [[ "$DRY_RUN" -eq 1 ]]; then
  mkdir -p "$DATA_DIR/personal_samples" "$DATA_DIR/trained_wake_words" 2>/dev/null || true
else
  mkdir -p "$DATA_DIR/personal_samples" "$DATA_DIR/trained_wake_words"
fi

PERSONAL_CANDIDATES=(
  "${MWW_PERSONAL_SRC:-}"
  "$SCRIPT_DIR/personal_samples"
  "${WAKEWORD_TRAINER_DATA_DIR:-$HOME/.taterwakewordtrainer/app/current}/personal_samples"
)
if [[ "$DRY_RUN" -eq 0 ]]; then
  for src in "${PERSONAL_CANDIDATES[@]}"; do
    [[ -n "$src" && -d "$src" ]] || continue
    wav_count="$(find "$src" -maxdepth 1 -type f \( -name '*.wav' -o -name '*.WAV' \) 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "${wav_count:-0}" -gt 0 ]]; then
      log "Copiando $wav_count WAV desde $src"
      "$SCRIPT_DIR/export_personal_samples.sh" --src "$src" --dest "$DATA_DIR/personal_samples"
      break
    fi
  done
fi

if [[ "$DRY_RUN" -eq 0 ]] && ! command -v docker >/dev/null 2>&1; then
  die "docker no está en PATH. En Windows 11 instala Docker Desktop con backend WSL2."
fi

run_cmd docker pull "$IMAGE"

# Bridge + -p: --network host no funciona igual en Docker Desktop Windows.
if [[ "$CPU" -eq 1 ]]; then
  DOCKER_RUN=(
    docker run -d
    --name "$CONTAINER_NAME"
    -p "${REC_PORT}:${REC_PORT}"
    -e "REC_PORT=${REC_PORT}"
    -v "${DATA_DIR}:/data"
    "$IMAGE"
  )
else
  DOCKER_RUN=(
    docker run -d
    --name "$CONTAINER_NAME"
    --gpus all
    -p "${REC_PORT}:${REC_PORT}"
    -e "REC_PORT=${REC_PORT}"
    -v "${DATA_DIR}:/data"
    "$IMAGE"
  )
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf '[dry-run] %s\n' "${DOCKER_RUN[*]}"
else
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    log "Contenedor $CONTAINER_NAME ya existe — no se recrea (docker start $CONTAINER_NAME)"
    log "Si se creó con --gpus all en un PC AMD: docker rm -f $CONTAINER_NAME && $0 --cpu"
    docker start "$CONTAINER_NAME" >/dev/null || true
  else
    "${DOCKER_RUN[@]}"
  fi
fi

log "UI del trainer: http://127.0.0.1:${REC_PORT}"
log "Wake word: mariano | idioma: Spanish | muestras: /data/personal_samples"
log "Tras entrenar: $DATA_DIR/trained_wake_words/mariano.{tflite,json}"
if [[ "$CPU" -eq 1 ]]; then
  log "CPU: más lento; 16 GB RAM es justo — cierra el resto de apps"
fi
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry-run: no se ha lanzado docker"
fi
