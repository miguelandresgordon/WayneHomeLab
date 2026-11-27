#!/usr/bin/env bash
# lab.sh — atajos del laboratorio (ver docs/hacking-lab.md)
#   ./lab.sh up | up-full | tor | shell | targets | verify | down
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

case "${1:-}" in
  up) docker compose up -d --build ;;
  up-full) docker compose --profile full up -d --build ;;
  tor) docker compose --profile tor up -d --build tor ;;
  shell) docker compose exec kali bash ;;
  targets)
    echo "Desde Kali (./lab.sh shell):"
    echo "  Juice Shop  http://juice-shop:3000"
    echo "  DVWA        http://dvwa  (admin / password; Setup -> Create DB)"
    echo "  WebGoat     http://webgoat:8080/WebGoat  (perfil full)"
    ;;
  verify) ./verify_lab.sh ;;
  down) docker compose --profile full --profile tor down ;;
  *) echo "uso: $0 up|up-full|tor|shell|targets|verify|down" >&2; exit 2 ;;
esac
