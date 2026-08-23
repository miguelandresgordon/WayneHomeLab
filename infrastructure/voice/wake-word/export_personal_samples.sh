#!/usr/bin/env bash
# export_personal_samples.sh — Copia WAV de wake word a una carpeta de transferencia
#
# No reconstruye padding: copia los WAV ya preparados (personal_NNN.wav) o
# cualquier *.wav del origen. Ignora .txt/.zip/.DS_Store.
#
# Uso:
#   ./export_personal_samples.sh
#   ./export_personal_samples.sh --src ~/.taterwakewordtrainer/app/current/personal_samples
#   ./export_personal_samples.sh --src DIR --dest DIR
# macOS zsh: zsh ./export_personal_samples.sh

set -euo pipefail

_this="$0"
if [ -n "${BASH_VERSION:-}" ]; then
  _this="${BASH_SOURCE[0]}"
fi
SCRIPT_DIR="$(cd "$(dirname "$_this")" && pwd)"
SUPPORT_DIR="${WAKEWORD_TRAINER_SUPPORT_DIR:-$HOME/.taterwakewordtrainer}"
DATA_DIR="${WAKEWORD_TRAINER_DATA_DIR:-$SUPPORT_DIR/app/current}"
SRC="${MWW_PERSONAL_SRC:-$DATA_DIR/personal_samples}"
DEST="${MWW_PERSONAL_EXPORT_DIR:-$SCRIPT_DIR/personal_samples}"

log() { printf '[export-personal-samples] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--src DIR] [--dest DIR] [--help]

  --src DIR   Origen de WAV (default: $SRC)
  --dest DIR  Destino de transferencia (default: $DEST)
  --help      Esta ayuda

Copia solo *.wav (no AppleDouble ._*). Imprime exported_personal_wavs=N
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src)  SRC="$2"; shift 2 ;;
    --dest) DEST="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

if [[ ! -d "$SRC" ]]; then
  die "No se encontraron muestras personales: $SRC"
fi

shopt -s nullglob
wavs=()
for f in "$SRC"/*.wav "$SRC"/*.WAV; do
  base="$(basename "$f")"
  [[ "$base" == ._* ]] && continue
  wavs+=("$f")
done
shopt -u nullglob

if [[ ${#wavs[@]} -eq 0 ]]; then
  die "No se encontraron archivos .wav en $SRC"
fi

mkdir -p "$DEST"
copied=0
for f in "${wavs[@]}"; do
  cp "$f" "$DEST/$(basename "$f")"
  copied=$((copied + 1))
done

log "exported_personal_wavs=${copied} dest=$DEST"
printf 'exported_personal_wavs=%s dest=%s\n' "$copied" "$DEST"
