#!/usr/bin/env bash
# free_trainer_disk.sh — Libera espacio en disco del trainer MWW
#
# El entrenamiento escribe datasets en ~/.taterwakewordtrainer/app/current
# (no en el clone del repo). Requiere ~25 GB libres durante AudioSet/FMA.
#
# Uso:
#   ./free_trainer_disk.sh                 # limpia parciales + brew cache
#   ./free_trainer_disk.sh --resume        # zips negativos + WAV 16k + tts-envs (conserva features/TTS)
#   ./free_trainer_disk.sh --aggressive    # borra features rebuildables + audioset/fma/chime crudos
#   ./free_trainer_disk.sh --keep-personal # borra TTS/features/datasets; conserva solo personal_samples

set -euo pipefail

SUPPORT_DIR="${WAKEWORD_TRAINER_SUPPORT_DIR:-$HOME/.taterwakewordtrainer}"
DATA_DIR="${WAKEWORD_TRAINER_DATA_DIR:-$SUPPORT_DIR/app/current}"
TRAINER_DIR="${MWW_TRAINER_DIR:-$HOME/Proyectos/microWakeWord-Trainer-AppleSilicon}"
MODE=""

GENERATED_DIRS=(
  generated_samples
  generated_augmented_features
  personal_augmented_features
  reviewed_negative_features
  negative_datasets
  negative_samples
  mit_rirs
  audioset
  audioset_16k
  fma
  fma_16k
  chime
  chime_16k
  piper-sample-generator
  tts-envs
  micro-wake-word
  captured_audio
  trained_wake_words
  trim_history
)
HIDDEN_GENERATED_DIRS=(.cache .venv .venv-blackwell)

log() { printf '[free-trainer-disk] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--resume|--aggressive|--keep-personal|--help]

  (sin flags)        Limpia parciales de descarga + brew cache
  --resume           Conserva features/TTS; borra zips negativos y WAV 16k
  --aggressive       Borra features rebuildables y datasets crudos (audioset/fma/chime)
  --keep-personal    Borra TTS, features, datasets y caches. Conserva solo personal_samples/
  --help             Esta ayuda

Variables:
  WAKEWORD_TRAINER_DATA_DIR=$DATA_DIR
  FREE_TRAINER_SKIP_BREW=${FREE_TRAINER_SKIP_BREW:-0}
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resume|--aggressive|--keep-personal) MODE="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

free_space() {
  if [[ -d /System/Volumes/Data ]]; then
    df -h /System/Volumes/Data | awk 'NR==2 {print $4}'
  else
    df -h "${DATA_DIR:-.}" | awk 'NR==2 {print $4}'
  fi
}

remove_dir() {
  local path="$1"
  if [[ -e "$path" ]]; then
    log "Eliminando $path"
    rm -rf "$path"
  fi
}

keep_personal_cleanup() {
  log "Modo keep-personal: conservar solo muestras personales"
  local name
  for name in "${GENERATED_DIRS[@]}" "${HIDDEN_GENERATED_DIRS[@]}"; do
    remove_dir "$DATA_DIR/$name"
  done
  if [[ -d "$DATA_DIR" ]]; then
    find "$DATA_DIR" -maxdepth 1 -type f \( -name '*.log' -o -name '*.pid' \) -print -delete 2>/dev/null \
      | while read -r f; do log "Eliminado $f"; done || true
  fi
  local count=0
  if [[ -d "$DATA_DIR/personal_samples" ]]; then
    count="$(find "$DATA_DIR/personal_samples" -type f -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')"
  fi
  log "Muestras personales conservadas: ${count} WAV en $DATA_DIR/personal_samples/"
}

log "DATA_DIR=$DATA_DIR"
log "Espacio libre antes: $(free_space)"

if [[ "${FREE_TRAINER_SKIP_BREW:-0}" != "1" ]] && command -v brew >/dev/null 2>&1; then
  brew cleanup -s 2>/dev/null || true
fi

# Limpieza en data dir real + clone legacy (por si quedó basura antigua)
for root in "$DATA_DIR" "$TRAINER_DIR"; do
  [[ -d "$root" ]] || continue
  if [[ -d "$root/audioset" ]]; then
    find "$root/audioset" -name '*.tar.partial' -delete 2>/dev/null || true
    find "$root/audioset" -name '*.tmp' -delete 2>/dev/null || true
  fi
done

if [[ "$MODE" == "--keep-personal" ]]; then
  keep_personal_cleanup
fi

if [[ "$MODE" == "--resume" ]]; then
  log "Modo resume: conservar features, TTS y muestras personales"
  if [[ -d "$DATA_DIR/negative_datasets" ]]; then
    find "$DATA_DIR/negative_datasets" -maxdepth 1 -type f -name '*.zip' -print -delete 2>/dev/null \
      | while read -r f; do log "Eliminado zip: $f"; done || true
  fi
  if [[ -f "$DATA_DIR/generated_augmented_features/.cache_key" ]]; then
    for d in fma_16k chime_16k audioset_16k mit_rirs; do
      if [[ -d "$DATA_DIR/$d" ]]; then
        log "Eliminando $DATA_DIR/$d (features ya cacheadas)..."
        rm -rf "$DATA_DIR/$d"
      fi
    done
  fi
  sample_count="$(find "$DATA_DIR/generated_samples" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "${sample_count:-0}" -gt 100 && -d "$DATA_DIR/tts-envs" ]]; then
    log "Eliminando $DATA_DIR/tts-envs (TTS ya generado: ${sample_count} WAV)..."
    rm -rf "$DATA_DIR/tts-envs"
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -m pip cache purge >/dev/null 2>&1 || true
  fi
fi

if [[ "$MODE" == "--aggressive" ]]; then
  cleaned=0
  for feat in generated_augmented_features personal_augmented_features reviewed_negative_features; do
    if [[ -d "$DATA_DIR/$feat" ]]; then
      log "Eliminando $DATA_DIR/$feat (rebuildable)..."
      rm -rf "$DATA_DIR/$feat"
      cleaned=1
    fi
  done
  for root in "$DATA_DIR" "$TRAINER_DIR"; do
    [[ -d "$root" ]] || continue
    if [[ -d "$root/audioset" ]]; then
      wav_count="$(find "$root/audioset_16k" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')"
      if [[ "${wav_count:-0}" -gt 1000 ]]; then
        log "Eliminando $root/audioset (${wav_count} WAV en audioset_16k)..."
        rm -rf "$root/audioset"
        cleaned=1
      else
        log "audioset_16k incompleto en $root ($wav_count WAV) — no se elimina audioset crudo"
      fi
    fi
    for pair in "fma:fma_16k" "chime:chime_16k"; do
      raw="${pair%%:*}"
      cooked="${pair##*:}"
      if [[ -d "$root/$raw" && -d "$root/$cooked" ]]; then
        wav_count="$(find "$root/$cooked" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')"
        if [[ "${wav_count:-0}" -gt 100 ]]; then
          log "Eliminando $root/$raw (${wav_count} WAV en $cooked)..."
          rm -rf "$root/$raw"
          cleaned=1
        fi
      fi
    done
  done
  for d in audioset_16k fma_16k chime_16k; do
    [[ -d "$DATA_DIR/$d" ]] || continue
    n="$(find "$DATA_DIR/$d" -name '*.wav' \( -size 0 -o -size -100c \) -print -delete 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "${n:-0}" -gt 0 ]]; then
      log "Eliminados $n WAV inválidos en $d"
      cleaned=1
    fi
  done
  if [[ "$cleaned" -eq 0 ]]; then
    log "Nada agresivo que borrar"
  fi
fi

log "Espacio libre después: $(free_space)"
log "Top carpetas en DATA_DIR:"
if [[ -d "$DATA_DIR" ]]; then
  du -sh "$DATA_DIR"/*/ 2>/dev/null | sort -hr | head -10 || true
  du -sh "$DATA_DIR" 2>/dev/null || true
else
  log "DATA_DIR no existe aún (se creará en el primer train)"
fi
