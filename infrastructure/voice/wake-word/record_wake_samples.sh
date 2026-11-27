#!/usr/bin/env bash
# record_wake_samples.sh — Graba positivos «Mariano» (2 s, 16000 Hz mono) en el
# MacBook Air para reentrenar con ruido de reproducción (F3c). Sin gasto.
#
#   ./record_wake_samples.sh alicia radio_alta 10
#   ./record_wake_samples.sh miguel normal 10
#
# Condiciones del guion (guion_muestras_mariano.md): normal, voz_alta, lejos,
# radio_alta, musica_alta, tele. Salida: personal_samples/<persona>_<cond>_NNN.wav
# (gitignored). Micro: el integrado (avfoundation ":0"; cambia con MIC=":1").
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/personal_samples"
MIC="${MIC:-:0}"

main() {
  local persona="${1:?uso: record_wake_samples.sh <alicia|miguel> <condición> [n]}"
  local cond="${2:?condición: normal|voz_alta|lejos|radio_alta|musica_alta|tele}"
  local n="${3:-10}"
  [[ "$persona" =~ ^[a-z]+$ && "$cond" =~ ^[a-z_]+$ ]] || { echo "minúsculas, sin espacios" >&2; exit 2; }
  command -v ffmpeg >/dev/null || { echo "instala ffmpeg (brew install ffmpeg)" >&2; exit 1; }
  mkdir -p "$OUT_DIR"
  local start i f
  start="$(find "$OUT_DIR" -name "${persona}_${cond}_*.wav" | wc -l | tr -d ' ')"
  for ((i = 1; i <= n; i++)); do
    f="$OUT_DIR/${persona}_${cond}_$(printf '%03d' $((start + i))).wav"
    read -r -p "[$i/$n] Enter y di «Mariano» (2 s)... " _
    ffmpeg -hide_banner -loglevel error -y -f avfoundation -i "$MIC" -t 2 -ar 16000 -ac 1 -c:a pcm_s16le "$f"
    echo "  -> $(basename "$f")"
  done
  echo "Listo: $(find "$OUT_DIR" -name "${persona}_*.wav" | wc -l | tr -d ' ') muestras de $persona en $OUT_DIR"
}

main "$@"
