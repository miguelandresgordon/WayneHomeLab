#!/usr/bin/env bash
# run_capture_workflow.sh — Orquesta captura de muestras + re-entrenamiento (TDD workflow)
#
# Uso:
#   ./run_capture_workflow.sh check     # verifica prerequisitos
#   ./run_capture_workflow.sh retrain   # re-entrena con personal/negative samples

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINER_DIR="${MWW_TRAINER_DIR:-$HOME/Proyectos/microWakeWord-Trainer-AppleSilicon}"

log() { printf '[capture-workflow] %s\n' "$*"; }
fail() { log "FAIL: $*"; exit 1; }

check_prerequisites() {
  log "Verificando prerequisitos de captura..."

  [[ -d "$TRAINER_DIR" ]] || fail "Trainer no encontrado: $TRAINER_DIR"
  [[ -x "$SCRIPT_DIR/flash_capture_firmware.sh" ]] || fail "flash_capture_firmware.sh missing"

  personal_count=0
  negative_count=0
  if [[ -d "$TRAINER_DIR/personal_samples" ]]; then
    personal_count="$(find "$TRAINER_DIR/personal_samples" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')"
  fi
  if [[ -d "$TRAINER_DIR/negative_samples" ]]; then
    negative_count="$(find "$TRAINER_DIR/negative_samples" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')"
  fi

  log "  personal_samples: $personal_count WAV"
  log "  negative_samples: $negative_count WAV"

  "$SCRIPT_DIR/flash_capture_firmware.sh"

  if [[ "$personal_count" -eq 0 ]]; then
    log "⚠️  Sin muestras personales — flash firmware captura y di 'Mariano' varias veces"
  fi
  if [[ "$negative_count" -eq 0 ]]; then
    log "⚠️  Sin negativas TV — marca falsos despertares como 'False wake' en Captured Audio"
  fi

  log "✅ Check completado"
}

retrain_with_samples() {
  log "Re-entrenando con muestras capturadas..."
  MWW_WAKE_WORD=mariano MWW_LANGUAGE=es "$SCRIPT_DIR/setup_trainer_macos.sh" train
  log "✅ Re-entrenamiento completado — ejecuta flash_mariano_firmware.sh"
}

case "${1:-check}" in
  check)   check_prerequisites ;;
  retrain) retrain_with_samples ;;
  *)
    echo "Uso: $0 [check|retrain]"
    exit 1
    ;;
esac
