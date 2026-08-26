#!/usr/bin/env bash
# setup_trainer_macos.sh — Instala y arranca microWakeWord-Trainer-AppleSilicon
#
# Uso:
#   ./setup_trainer_macos.sh              # clona (si falta) y arranca UI en :8789
#   ./setup_trainer_macos.sh ui           # idem
#   ./setup_trainer_macos.sh train        # delega en train_mariano_local.sh (recomendado)
#
# Para entrenamiento a prueba de sueño/cierre de terminal, preferir:
#   ./train_mariano_local.sh
#
# Requisitos: macOS Apple Silicon, Homebrew, python@3.11

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINER_DIR="${MWW_TRAINER_DIR:-$HOME/Proyectos/microWakeWord-Trainer-AppleSilicon}"
TRAINER_REPO="https://github.com/TaterTotterson/microWakeWord-Trainer-AppleSilicon.git"
WAKE_WORD="${MWW_WAKE_WORD:-mariano}"
LANGUAGE="${MWW_LANGUAGE:-es}"
MAX_SAMPLES="${MWW_MAX_SAMPLES:-18000}"
REC_PORT="${REC_PORT:-8789}"

log() { printf '[setup-trainer] %s\n' "$*"; }

ensure_python311() {
  if [[ ! -x /opt/homebrew/bin/python3.11 ]]; then
    log "Instalando python@3.11..."
    brew install python@3.11
  fi
}

ensure_trainer_repo() {
  if [[ ! -d "$TRAINER_DIR/.git" ]]; then
    log "Clonando trainer en $TRAINER_DIR"
    git clone --depth 1 "$TRAINER_REPO" "$TRAINER_DIR"
  else
    log "Trainer ya presente en $TRAINER_DIR"
  fi
}

start_ui() {
  cd "$TRAINER_DIR"
  log "Arrancando UI en http://127.0.0.1:${REC_PORT}"
  log "Para captura desde Satellite1, configura Trainer App URL: http://$(ipconfig getifaddr en0 2>/dev/null || echo 'TU_IP_MAC'):${REC_PORT}"
  REC_PYTHON_BIN=/opt/homebrew/bin/python3.11 REC_PORT="$REC_PORT" ./run.sh
}

train_cli() {
  log "Delegando en train_mariano_local.sh (caffeinate + nohup, ${MAX_SAMPLES} muestras)..."
  log "caffeinate solo no basta: el script también usa nohup/disown."
  export MWW_WAKE_WORD="$WAKE_WORD"
  export MWW_LANGUAGE="$LANGUAGE"
  export MWW_MAX_SAMPLES="$MAX_SAMPLES"
  exec "$SCRIPT_DIR/train_mariano_local.sh"
}

main() {
  ensure_python311
  ensure_trainer_repo

  case "${1:-ui}" in
    ui|run|start) start_ui ;;
    train)        train_cli ;;
    *)
      echo "Uso: $0 [ui|train]"
      echo "  ui     — UI en :${REC_PORT}"
      echo "  train  — llama a train_mariano_local.sh (recomendado)"
      exit 1
      ;;
  esac
}

main "$@"
