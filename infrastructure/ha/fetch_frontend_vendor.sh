#!/usr/bin/env bash
# fetch_frontend_vendor.sh — Descarga las tarjetas de terceros que usan los
# dashboards, con versión y SHA-256 fijados, a home-assistant/www/wayne/vendor/
# (gitignored; deploy_ha_voice_config.sh lo copia a /config/www/wayne/vendor).
# HA lo sirve en local (/local/wayne/vendor/...): sin peticiones externas en uso.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$REPO_ROOT/home-assistant/www/wayne/vendor"

# nombre|versión|url|sha256
VENDOR=(
  "apexcharts-card.js|v2.2.3|https://github.com/RomRider/apexcharts-card/releases/download/v2.2.3/apexcharts-card.js|346780707773fb90c45e9eeaf8acb010d16a8089e86563a242cc4e1d8995f718"
)

log() { printf '[vendor] %s\n' "$*"; }

sha256_of() { shasum -a 256 "$1" | awk '{print $1}'; }

main() {
  mkdir -p "$DEST"
  local entry name version url sum tmp
  for entry in "${VENDOR[@]}"; do
    IFS='|' read -r name version url sum <<<"$entry"
    if [[ -f "$DEST/$name" && "$(sha256_of "$DEST/$name")" == "$sum" ]]; then
      log "$name $version ya presente (sha256 OK)"
      continue
    fi
    tmp="$(mktemp)"
    curl -fsSL -o "$tmp" "$url"
    if [[ "$(sha256_of "$tmp")" != "$sum" ]]; then
      rm -f "$tmp"
      log "❌ sha256 no coincide para $name $version"
      exit 1
    fi
    mv "$tmp" "$DEST/$name"
    chmod 644 "$DEST/$name"
    log "$name $version descargado y verificado"
  done
}

main "$@"
