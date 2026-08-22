#!/usr/bin/env bash
# train_mariano_local.sh — Entrena wake word "mariano" en local (Mac Apple Silicon)
#
# Evita cortes por sueño (caffeinate) y por cierre de terminal (nohup+disown).
# caffeinate SOLO no basta: hace falta desacoplar el proceso del shell.
#
# Uso:
#   ./train_mariano_local.sh                  # 18000 muestras, copia ~/Desktop/mariano_raw
#   ./train_mariano_local.sh --no-copy-personal
#   MWW_MAX_SAMPLES=8000 ./train_mariano_local.sh
#   ./train_mariano_local.sh --foreground     # sin nohup (útil para depurar)
#
# Requisitos: ~25 GB libres, python@3.11, clone del trainer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINER_DIR="${MWW_TRAINER_DIR:-$HOME/Proyectos/microWakeWord-Trainer-AppleSilicon}"
SUPPORT_DIR="${WAKEWORD_TRAINER_SUPPORT_DIR:-$HOME/.taterwakewordtrainer}"
DATA_DIR="${WAKEWORD_TRAINER_DATA_DIR:-$SUPPORT_DIR/app/current}"
WAKE_WORD="${MWW_WAKE_WORD:-mariano}"
LANGUAGE="${MWW_LANGUAGE:-es}"
MAX_SAMPLES="${MWW_MAX_SAMPLES:-18000}"
MIN_FREE_GB="${MWW_MIN_FREE_GB:-25}"
PERSONAL_SRC="${MWW_PERSONAL_SRC:-$HOME/Desktop/mariano_raw}"
COPY_PERSONAL=1
FOREGROUND=0

log() { printf '[train-mariano-local] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--no-copy-personal] [--foreground] [--help]

  --no-copy-personal  No copiar WAV desde \$MWW_PERSONAL_SRC ($PERSONAL_SRC)
  --foreground        Ejecutar en primer plano (sin nohup/disown)
  --help              Esta ayuda

Variables:
  MWW_MAX_SAMPLES=$MAX_SAMPLES
  MWW_MIN_FREE_GB=$MIN_FREE_GB
  MWW_WAKE_WORD=$WAKE_WORD
  MWW_LANGUAGE=$LANGUAGE
  MWW_PERSONAL_SRC=$PERSONAL_SRC
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-copy-personal) COPY_PERSONAL=0; shift ;;
    --foreground)       FOREGROUND=1; shift ;;
    -h|--help)          usage; exit 0 ;;
    *)                  die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

free_gb() {
  df -g /System/Volumes/Data | awk 'NR==2 {print $4}'
}

ensure_trainer() {
  if [[ ! -x "$TRAINER_DIR/train_microwakeword_macos.sh" ]]; then
    die "Falta $TRAINER_DIR/train_microwakeword_macos.sh — clona el trainer o ejecuta setup_trainer_macos.sh ui una vez"
  fi
}

copy_personal_samples() {
  if [[ ! -d "$PERSONAL_SRC" ]]; then
    log "No hay carpeta de muestras personales: $PERSONAL_SRC (sigo sin copiar)"
    return 0
  fi
  local out count
  out="$(python3 "$SCRIPT_DIR/pad_personal_samples.py" "$PERSONAL_SRC" "$DATA_DIR/personal_samples" --pad-ms 100)"
  count="${out#padded_personal_wavs=}"
  count="${count%% *}"
  log "$out"
  log "Muestras personales copiadas+padded (100 ms silencio): ${count:-0} → $DATA_DIR/personal_samples/"
}

# --- prechecks ---
MIN_SAMPLES_FOR_RESUME_CHECK="${MWW_MIN_SAMPLES_FOR_RESUME:-1000}"
RESUME_MIN_FREE_GB="${MWW_RESUME_MIN_FREE_GB:-12}"

check_disk_space() {
  local available="$1"
  local min_gb="$MIN_FREE_GB"
  if [[ -f "$DATA_DIR/generated_augmented_features/.cache_key" ]]; then
    local tts_count
    tts_count="$(find "$DATA_DIR/generated_samples" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "${tts_count:-0}" -ge "$MIN_SAMPLES_FOR_RESUME_CHECK" ]]; then
      min_gb="$RESUME_MIN_FREE_GB"
      log "Features+TTS cache detectados → mínimo disco resume=${min_gb} GB (override: MWW_RESUME_MIN_FREE_GB)"
    fi
  fi
  log "Espacio libre: ${available} GB (mínimo ${min_gb} GB)"
  if [[ "$available" -lt "$min_gb" ]]; then
    die "Poco disco. Ejecuta: $SCRIPT_DIR/free_trainer_disk.sh --resume (o --aggressive si aún falta espacio)"
  fi
}

check_disk_space "$(free_gb)"

ensure_trainer
mkdir -p "$DATA_DIR"

if [[ "$COPY_PERSONAL" -eq 1 ]]; then
  copy_personal_samples
fi

# AudioSet a veces deja WAV vacíos que rompen AddBackgroundNoise (ValueError: empty array)
scrub_bad_background_wavs() {
  local d f
  for d in audioset_16k fma_16k chime_16k; do
    [[ -d "$DATA_DIR/$d" ]] || continue
    find "$DATA_DIR/$d" -name '*.wav' \( -size 0 -o -size -100c \) -print -delete 2>/dev/null \
      | while read -r f; do log "Eliminado WAV inválido: $f"; done || true
  done
}
scrub_bad_background_wavs

log "Descargando voces Piper ES (si faltan)..."
"$SCRIPT_DIR/download_piper_voices_es.sh" || true

LOG_FILE="$TRAINER_DIR/training_${WAKE_WORD}.log"
PID_FILE="$TRAINER_DIR/training_${WAKE_WORD}.pid"

export WAKEWORD_TRAINER_SUPPORT_DIR="$SUPPORT_DIR"
export WAKEWORD_TRAINER_DATA_DIR="$DATA_DIR"
export MWW_ARTIFACT_SLUG="$WAKE_WORD"

TRAIN_CMD=(
  "$TRAINER_DIR/train_microwakeword_macos.sh"
  "$WAKE_WORD"
  "$MAX_SAMPLES"
  "100"
  --language "$LANGUAGE"
)

log "Wake word=$WAKE_WORD language=$LANGUAGE samples=$MAX_SAMPLES"
log "DATA_DIR=$DATA_DIR"
log "Log: $LOG_FILE"

export PYTHONUNBUFFERED=1
export PYTHONUNBUFFERED

if [[ "$FOREGROUND" -eq 1 ]]; then
  log "Modo foreground (Ctrl+C corta el train)"
  caffeinate -dims env PYTHONUNBUFFERED=1 "${TRAIN_CMD[@]}" 2>&1 | tee "$LOG_FILE"
  "$SCRIPT_DIR/copy_model_from_trainer.sh" || true
  exit 0
fi

# Background: nohup desacopla del terminal; caffeinate evita sueño.
# Importante: caffeinate envuelve el train (no al revés con nohup mal anidado).
: >"$LOG_FILE"
{
  echo "[train-mariano-local] start $(date -Iseconds) pid_wrapper=$$"
  cd "$TRAINER_DIR"
  # shellcheck disable=SC2090
  nohup caffeinate -dims env PYTHONUNBUFFERED=1 "${TRAIN_CMD[@]}" >>"$LOG_FILE" 2>&1
  rc=$?
  echo "[train-mariano-local] train exit_code=$rc finished $(date -Iseconds)" >>"$LOG_FILE"
  if [[ $rc -eq 0 ]]; then
    "$SCRIPT_DIR/copy_model_from_trainer.sh" >>"$LOG_FILE" 2>&1 || true
  fi
} &
TRAIN_PID=$!
echo "$TRAIN_PID" >"$PID_FILE"
disown "$TRAIN_PID" 2>/dev/null || true

log "Entrenamiento lanzado en background (pid=$TRAIN_PID)"
log "Seguir log:   tail -f $LOG_FILE"
log "¿Sigue vivo?: ps -p $TRAIN_PID"
log "Artefactos:   $DATA_DIR/trained_wake_words/${WAKE_WORD}.{tflite,json}"
log "Al terminar (si OK) se copia a $SCRIPT_DIR/models/"
log "Si el log se para tras 'Pinned ML stack verified', espera: pip -q no imprime nada unos minutos."
