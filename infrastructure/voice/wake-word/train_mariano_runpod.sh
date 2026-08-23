#!/usr/bin/env bash
# train_mariano_runpod.sh — Sincroniza personal_samples y deja el CLI RunPod listo
#
# Exporta WAV locales (padded) y documenta runpodctl send + train_wake_word
# en tmux dentro del GPU Pod. No lanza el train remoto (no hay API key aquí).
# macOS zsh: zsh ./train_mariano_runpod.sh --dry-run

set -euo pipefail

_this="$0"
if [ -n "${BASH_VERSION:-}" ]; then
  _this="${BASH_SOURCE[0]}"
fi
SCRIPT_DIR="$(cd "$(dirname "$_this")" && pwd)"
STAGE_DIR="${MWW_RUNPOD_STAGE_DIR:-$SCRIPT_DIR/personal_samples}"
WAKE_WORD="${MWW_WAKE_WORD:-mariano}"
REC_PORT="${REC_PORT:-8789}"
POD_ID="${MWW_RUNPOD_POD_ID:-POD_ID}"
DRY_RUN=0

log() { printf '[train-mariano-runpod] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--dry-run] [--help]

Sincroniza personal_samples al staging local y imprime runpodctl send
más el comando train_wake_word en el GPU Pod (wake word ${WAKE_WORD}, Spanish).

  --dry-run   No copia WAV; imprime conteo y los comandos remotos
  --help      Esta ayuda

Variables:
  MWW_PERSONAL_SRC          origen de WAV (si está vacío, busca candidatos)
  MWW_RUNPOD_STAGE_DIR=$STAGE_DIR
  MWW_RUNPOD_POD_ID=$POD_ID
  MWW_WAKE_WORD=$WAKE_WORD
  MWW_RUNPOD_DATA_DIR       destino local al recibir el modelo (\$HOME/mww-runpod)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

sync_samples() {
  local src dest count
  dest="$STAGE_DIR"
  mkdir -p "$dest"
  local candidates=()
  if [[ -n "${MWW_PERSONAL_SRC:-}" ]]; then
    candidates=("$MWW_PERSONAL_SRC")
  else
    candidates=(
      "$SCRIPT_DIR/personal_samples"
      "${WAKEWORD_TRAINER_DATA_DIR:-$HOME/.taterwakewordtrainer/app/current}/personal_samples"
    )
  fi
  for src in "${candidates[@]}"; do
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
  log "Sin WAV de personal_samples que copiar (súbelos al pod en /data/personal_samples)"
}

log "Wake word=$WAKE_WORD UI=:${REC_PORT}  staging=$STAGE_DIR"
sync_samples

cat <<EOF

--- En el GPU Pod (Web Terminal o SSH; usa tmux/nohup para no cortar al cerrar el browser) ---
nvidia-smi
mkdir -p /data/personal_samples /data/trained_wake_words
tmux new -s ${WAKE_WORD} || tmux attach -t ${WAKE_WORD}
train_wake_word --language=Spanish ${WAKE_WORD}
# artefactos: /data/trained_wake_words/${WAKE_WORD}.{tflite,json}

--- Subir muestras desde este PC ---
runpodctl send ${STAGE_DIR} ${POD_ID}
# o scp los WAV a /data/personal_samples/

--- Bajar modelo (local) ---
runpodctl receive ${POD_ID}:/data/trained_wake_words/${WAKE_WORD}.tflite
runpodctl receive ${POD_ID}:/data/trained_wake_words/${WAKE_WORD}.json
mkdir -p "\${MWW_RUNPOD_DATA_DIR:-\$HOME/mww-runpod}/trained_wake_words"
# luego:
#   MWW_RUNPOD_DATA_DIR=\$HOME/mww-runpod $SCRIPT_DIR/copy_model_from_trainer.sh

UI alternativa: Connect → HTTP ${REC_PORT} → Trainer → ${WAKE_WORD} / Spanish → confirma personal_samples → Start training.
Al terminar (en este PC, tras tener los .tflite/.json locales):
  $SCRIPT_DIR/teardown_runpod_trainer.sh --dry-run
  MWW_RUNPOD_POD_ID=${POD_ID} $SCRIPT_DIR/teardown_runpod_trainer.sh
  # Borrar volume (opt-in): --delete-volume + MWW_RUNPOD_VOLUME_ID=...
  # --watch espera artefactos (SSH o ficheros locales). No pares el pod a mano antes de descargar.
EOF

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry-run: no se ha enviado nada a RunPod"
fi
