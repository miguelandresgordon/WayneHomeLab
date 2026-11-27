#!/usr/bin/env bash
# verify_lab.sh — comprueba el aislamiento del laboratorio (docs/hacking-lab.md)
#
#   ./verify_lab.sh            # IP pública, fuga de DNS, objetivos sin salida
#   ./verify_lab.sh --kill     # + prueba del kill switch (tumba wg0 y reinicia)
#
# Requiere el laboratorio arrancado (./lab.sh up) con TU clave de Mullvad en .env.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

FAILS=0
pass() { printf 'OK    %s\n' "$*"; }
fail() { printf 'FALLO %s\n' "$*"; FAILS=$((FAILS + 1)); }
kexec() { docker compose exec -T kali "$@"; }

check_running() {
  if ! docker compose ps --status running --services | grep -qx kali; then
    echo "El laboratorio no está arrancado (./lab.sh up)." >&2
    exit 2
  fi
}

check_public_ip() {
  local json
  json="$(kexec curl -fsS --max-time 15 https://am.i.mullvad.net/json || true)"
  if [ -n "$json" ] && printf '%s' "$json" | grep -q '"mullvad_exit_ip": *true'; then
    pass "salida por Mullvad: $(printf '%s' "$json" | jq -r '.ip + " (" + .city + ")"' 2>/dev/null || echo '?')"
  else
    fail "Kali NO sale por Mullvad (am.i.mullvad.net): ${json:-sin respuesta}"
  fi
}

check_dns_leak() {
  # whoami.akamai.net devuelve la IP del resolvedor que pregunta a Akamai:
  # debe ser de Mullvad, nunca la IP de casa (fuga de DNS).
  local host_ip resolver
  host_ip="$(curl -fsS --max-time 10 https://am.i.mullvad.net/ip || true)"
  resolver="$(kexec dig +short +time=5 +tries=2 whoami.akamai.net | tail -1 || true)"
  if [ -z "$resolver" ]; then
    fail "sin resolución DNS desde Kali"
  elif [ -n "$host_ip" ] && [ "$resolver" = "$host_ip" ]; then
    fail "fuga de DNS: el resolvedor sale con la IP de casa ($resolver)"
  else
    pass "DNS por el túnel (resolvedor visto por Akamai: $resolver; casa: ${host_ip:-?})"
  fi
}

check_targets_reachable() {
  local t
  for t in juice-shop:3000 dvwa:80; do
    if kexec curl -fsS -o /dev/null --max-time 10 "http://$t/"; then
      pass "Kali llega a $t"
    else
      fail "Kali no llega a $t"
    fi
  done
}

check_targets_isolated() {
  # Contenedor desechable solo en lab_internal: no debe salir a internet.
  if docker run --rm --network hacking-lab_lab_internal --entrypoint curl \
      hacking-lab/kali:2026.11 -fsS -o /dev/null --max-time 8 https://1.1.1.1 2>/dev/null; then
    fail "lab_internal tiene salida a internet"
  else
    pass "lab_internal sin salida a internet"
  fi
}

check_kill_switch() {
  # Tumba el túnel: el firewall de gluetun debe bloquear toda salida.
  docker compose exec -T gluetun ip link set wg0 down
  if kexec curl -fsS -o /dev/null --max-time 8 https://1.1.1.1 2>/dev/null; then
    fail "kill switch: hay salida con wg0 caído"
  else
    pass "kill switch: sin salida con wg0 caído"
  fi
  echo "Restaurando el túnel (reinicio de gluetun y kali)…"
  docker compose restart gluetun >/dev/null
  docker compose up -d --force-recreate kali >/dev/null
}

main() {
  check_running
  check_public_ip
  check_dns_leak
  check_targets_reachable
  check_targets_isolated
  if [ "${1:-}" = "--kill" ]; then
    check_kill_switch
  fi
  if [ "$FAILS" -gt 0 ]; then
    echo "$FAILS comprobación(es) fallidas: NO uses el laboratorio." >&2
    exit 1
  fi
  echo "Laboratorio aislado y saliendo por Mullvad."
}

main "$@"
