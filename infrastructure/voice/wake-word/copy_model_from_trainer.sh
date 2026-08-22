#!/usr/bin/env bash
# copy_model_from_trainer.sh — Copia mariano.tflite/json del trainer al repo
#
# Artefactos reales viven en WAKEWORD_TRAINER_DATA_DIR (por defecto
# ~/.taterwakewordtrainer/app/current/trained_wake_words/), no en el clone.
# En Windows/Docker también busca $HOME/mww-data (MWW_NVIDIA_DATA_DIR).
#
# Uso: ./copy_model_from_trainer.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINER_DIR="${MWW_TRAINER_DIR:-$HOME/Proyectos/microWakeWord-Trainer-AppleSilicon}"
SUPPORT_DIR="${WAKEWORD_TRAINER_SUPPORT_DIR:-$HOME/.taterwakewordtrainer}"
DATA_DIR="${WAKEWORD_TRAINER_DATA_DIR:-$SUPPORT_DIR/app/current}"
NVIDIA_DATA="${MWW_NVIDIA_DATA_DIR:-$HOME/mww-data}"
DEST="$SCRIPT_DIR/models"
WAKE_WORD="${MWW_WAKE_WORD:-mariano}"

# Prefer data dir; fall back to Windows Docker volume and clone paths (legacy)
CANDIDATES=(
  "$DATA_DIR/trained_wake_words"
  "$NVIDIA_DATA/trained_wake_words"
  "$TRAINER_DIR/trained_wake_words"
  "$SUPPORT_DIR/trained_wake_words"
)

SRC_DIR=""
for d in "${CANDIDATES[@]}"; do
  if [[ -f "$d/${WAKE_WORD}.tflite" && -f "$d/${WAKE_WORD}.json" ]]; then
    SRC_DIR="$d"
    break
  fi
done

if [[ -z "$SRC_DIR" ]]; then
  echo "❌ No se encontraron artefactos ${WAKE_WORD}.{tflite,json}"
  echo "   Buscado en:"
  for d in "${CANDIDATES[@]}"; do
    echo "   - $d"
  done
  echo "   Espera a que termine el entrenamiento o revisa training_${WAKE_WORD}.log"
  exit 1
fi

mkdir -p "$DEST"
cp -v "$SRC_DIR/${WAKE_WORD}.tflite" "$SRC_DIR/${WAKE_WORD}.json" "$DEST/"
echo "✅ Modelo copiado desde $SRC_DIR → $DEST"
echo "   Sirve en LAN: $SCRIPT_DIR/serve_model.sh"
