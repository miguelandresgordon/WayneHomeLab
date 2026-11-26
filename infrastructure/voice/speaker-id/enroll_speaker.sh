#!/usr/bin/env bash
# enroll_speaker.sh — Enrola (o refuerza) a una persona con WAV del Satellite1.
#
#   1) Apunta la hora:  date +%Y-%m-%dT%H:%M
#   2) Di al Satellite1 las 12 frases de guion_enrolado.md (con «Mariano» delante)
#   3) ./enroll_speaker.sh alicia 2026-11-27T10:00
#
# Cadena: collect_satellite_samples.py -> train_profiles.py (todas las personas
# de samples/) -> validate_profiles.py -> deploy_to_haos.sh -> POST /reload.
# Requiere: /Volumes/share montado (Samba), SSH root@HAOS, sherpa-onnx en el venv.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
HA_HOST="${HA_HOST:-192.168.1.110}"
COUNT="${COUNT:-12}"

log() { printf '[enroll] %s\n' "$*"; }

python_bin() {
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
  else
    command -v python3
  fi
}

main() {
  local speaker="${1:?uso: enroll_speaker.sh <alicia|miguel> <desde: YYYY-MM-DDTHH:MM>}"
  local since="${2:?indica la hora de inicio de la sesión (date +%Y-%m-%dT%H:%M)}"
  local py
  py="$(python_bin)"
  [[ "$speaker" =~ ^[a-z]+$ ]] || { log "nombre en minúsculas sin espacios"; exit 2; }

  log "1/5 Recogiendo WAV del Satellite1 desde $since..."
  "$py" "$SCRIPT_DIR/collect_satellite_samples.py" --speaker "$speaker" --since "$since" --count "$COUNT"

  log "2/5 Entrenando perfiles (todas las personas en samples/)..."
  "$py" "$SCRIPT_DIR/train_profiles.py"

  log "3/5 Validando perfiles..."
  "$py" "$SCRIPT_DIR/validate_profiles.py" "$SCRIPT_DIR/export/speaker_profiles.json"

  log "4/5 Copiando a HAOS /share/speaker-id..."
  HA_HOST="$HA_HOST" "$SCRIPT_DIR/deploy_to_haos.sh"

  log "5/5 Recargando perfiles en el add-on..."
  curl -fsS -X POST "http://${HA_HOST}:10400/reload"
  echo
  curl -fsS "http://${HA_HOST}:10400/health"
  echo
  log "Listo. Prueba: di «Mariano, enciende la lámpara» y mira input_text.current_speaker."
}

main "$@"
