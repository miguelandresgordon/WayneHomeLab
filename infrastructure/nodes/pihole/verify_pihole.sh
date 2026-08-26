#!/usr/bin/env bash
# ==============================================================================
# verify_pihole.sh — Smoke-test Pi-hole DNS/UI from the Mac (or any LAN host)
#
# Usage:
#   bash infrastructure/nodes/pihole/verify_pihole.sh
#   PIHOLE_IP=192.168.1.53 bash infrastructure/nodes/pihole/verify_pihole.sh
#
# Does NOT change router DNS. Safe to run before cutover.
# Exit 0 if resolve + ping + UI checks pass.
# ==============================================================================
set -euo pipefail

PIHOLE_IP="${PIHOLE_IP:-192.168.1.53}"
BLOCK_TEST_DOMAIN="${BLOCK_TEST_DOMAIN:-doubleclick.net}"
ALLOW_TEST_DOMAIN="${ALLOW_TEST_DOMAIN:-google.com}"
failed=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

need_cmd() {
    command -v "$1" &>/dev/null || {
        log "ERROR: missing command: $1"
        exit 1
    }
}

dig_short() {
    # stdout only A/AAAA lines; empty on timeout / NXDOMAIN without answer
    dig +time=3 +tries=1 +short @"$PIHOLE_IP" "$1" 2>/dev/null || true
}

dig_ok() {
    # return 0 if dig got a response from the server (even NXDOMAIN)
    dig +time=3 +tries=1 @"$PIHOLE_IP" "$1" >/dev/null 2>&1
}

need_cmd dig
need_cmd curl
need_cmd ping

log "=== Pi-hole verify @ ${PIHOLE_IP} ==="

if ping -c 1 -W 2 "$PIHOLE_IP" &>/dev/null || ping -c 1 -t 2 "$PIHOLE_IP" &>/dev/null; then
    log "OK: ping ${PIHOLE_IP}"
else
    log "FAIL: ping ${PIHOLE_IP} (VM down or no reserva DHCP?)"
    failed=1
fi

if dig_ok "$ALLOW_TEST_DOMAIN"; then
    allow_ans="$(dig_short "$ALLOW_TEST_DOMAIN" | head -n1)"
    if [[ -n "$allow_ans" ]]; then
        log "OK: dig @${PIHOLE_IP} ${ALLOW_TEST_DOMAIN} → ${allow_ans}"
    else
        log "FAIL: dig @${PIHOLE_IP} ${ALLOW_TEST_DOMAIN} (no A record)"
        failed=1
    fi
else
    log "FAIL: dig @${PIHOLE_IP} ${ALLOW_TEST_DOMAIN} (no response / timeout)"
    failed=1
fi

if dig_ok "$BLOCK_TEST_DOMAIN"; then
    block_ans="$(dig_short "$BLOCK_TEST_DOMAIN" | head -n1)"
    if [[ -z "$block_ans" || "$block_ans" == "0.0.0.0" || "$block_ans" == "::" ]]; then
        log "OK: dig @${PIHOLE_IP} ${BLOCK_TEST_DOMAIN} blocked (${block_ans:-NXDOMAIN/NODATA})"
    else
        log "WARN: ${BLOCK_TEST_DOMAIN} → ${block_ans} (expected block; gravity may still be updating)"
    fi
else
    log "FAIL: dig @${PIHOLE_IP} ${BLOCK_TEST_DOMAIN} (no response / timeout)"
    failed=1
fi

if dig_ok "pi.hole"; then
    pihole_ans="$(dig_short pi.hole | head -n1)"
    if [[ -n "$pihole_ans" ]]; then
        log "OK: dig @${PIHOLE_IP} pi.hole → ${pihole_ans}"
    else
        log "WARN: pi.hole did not return an address (optional)"
    fi
else
    log "WARN: dig pi.hole timed out (optional)"
fi

http_code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 "http://${PIHOLE_IP}/admin" || true)"
if [[ -z "$http_code" || "$http_code" == "000" ]]; then
    log "FAIL: UI http://${PIHOLE_IP}/admin unreachable"
    failed=1
elif [[ "$http_code" =~ ^[23] ]]; then
    log "OK: HTTP ${http_code} http://${PIHOLE_IP}/admin"
else
    log "FAIL: UI http://${PIHOLE_IP}/admin → HTTP ${http_code}"
    failed=1
fi

echo ""
if [[ "$failed" -eq 0 ]]; then
    log "=== All critical checks passed ==="
    cat <<EOF
Cutover (manual — docs/pihole.md §4):
  1. Mac DNS → ${PIHOLE_IP}
  2. Un móvil / iPhone
  3. Router DNS LAN → ${PIHOLE_IP} (secundario 1.1.1.1 solo en burn-in)
Rollback: router DNS → ISP / 1.1.1.1
EOF
    exit 0
fi

log "=== Some checks failed — create/install VM first (docs/pihole.md) ==="
exit 1
