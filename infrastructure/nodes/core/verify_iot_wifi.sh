#!/usr/bin/env bash
# ==============================================================================
# verify_iot_wifi.sh — Diagnostica si los dispositivos IoT Wi-Fi 2,4 GHz
# (Satellite1, lámpara Xiaomi, bombilla Tuya) siguen en la LAN, y distingue
# «HA/Proxmox caídos» de «el Wi-Fi 2,4 GHz del router ya no los admite».
#
# Usage (desde el Mac, en la LAN):
#   bash infrastructure/nodes/core/verify_iot_wifi.sh
#   SATELLITE_IP=192.168.1.85 LAMP_IP=192.168.1.121 TUYA_IP=192.168.1.118 \
#     bash infrastructure/nodes/core/verify_iot_wifi.sh
#
# Solo lectura: no toca router, HA ni Proxmox.
# Exit 0 si todos responden; 1 si alguno falla (con veredicto de causa probable).
# ==============================================================================
set -euo pipefail

HA_IP="${HA_IP:-192.168.1.110}"
SATELLITE_IP="${SATELLITE_IP:-192.168.1.85}"   # ESPHome API 6053/tcp
LAMP_IP="${LAMP_IP:-192.168.1.121}"            # Xiaomi miIO 54321/udp
TUYA_IP="${TUYA_IP:-192.168.1.118}"            # Tuya local 6668/tcp (ver HA tuya_local)
LAN_CIDR="${LAN_CIDR:-192.168.1.0/24}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

need_cmd() {
    command -v "$1" &>/dev/null || {
        log "ERROR: missing command: $1"
        exit 1
    }
}

ping_ok() {
    # macOS: -W en ms; Linux: -W en s. Probar ambos.
    ping -c 2 -W 1000 "$1" &>/dev/null || ping -c 2 -W 1 "$1" &>/dev/null
}

arp_resolved() {
    # ARP refleja presencia L2 aunque el dispositivo ignore ICMP
    arp -n "$1" 2>/dev/null | grep -qi -E 'at ([0-9a-f]{1,2}:){5}[0-9a-f]{1,2}'
}

tcp_ok() { nc -z -G 2 -w 2 "$1" "$2" &>/dev/null || nc -z -w 2 "$1" "$2" &>/dev/null; }

miio_ok() {
    # Handshake miIO «hello»: 0x2131 + len 32 + 0xff…; cualquier respuesta = vivo
    printf '\x21\x31\x00\x20\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff' \
        | nc -u -w 2 "$1" 54321 2>/dev/null | xxd -p | grep -q .
}

check_device() {
    # check_device <label> <ip> <probe-fn> [probe-args…]
    local label="$1" ip="$2"
    shift 2
    ping_ok "$ip" || true   # solo calienta la tabla ARP
    if "$@" || arp_resolved "$ip"; then
        log "OK:   ${label} ${ip}"
        return 0
    fi
    log "FAIL: ${label} ${ip} (sin respuesta ni entrada ARP)"
    return 1
}

need_cmd nc
need_cmd xxd
need_cmd ping
need_cmd arp

log "=== IoT Wi-Fi verify (HA ${HA_IP}) ==="

# Control: HA y el resto de la LAN cableada/5 GHz deben estar vivos; si no,
# el problema es otro (Proxmox: ver «Proxmox cluster IPC» en AGENTS.md).
if ! tcp_ok "$HA_IP" 8123; then
    log "FAIL: HA ${HA_IP}:8123 caído → no es un problema de Wi-Fi; revisa Proxmox (qm start 100)"
    exit 1
fi
log "OK:   HA ${HA_IP}:8123"

failed=0
check_device "Satellite1 (ESPHome)" "$SATELLITE_IP" tcp_ok "$SATELLITE_IP" 6053 || failed=$((failed + 1))
check_device "Lámpara Xiaomi (miIO)" "$LAMP_IP" miio_ok "$LAMP_IP" || failed=$((failed + 1))
check_device "Bombilla Tuya" "$TUYA_IP" tcp_ok "$TUYA_IP" 6668 || failed=$((failed + 1))

if [[ "$failed" -eq 0 ]]; then
    log "=== Todos los dispositivos IoT responden ==="
    exit 0
fi

# ¿Cambiaron de IP? Barrido ARP de la LAN: si aparece la MAC del Satellite1
# (AGENTS.md) u otro chip Espressif (OUI 3c:0f:02) en otra IP, es DHCP, no Wi-Fi.
# macOS imprime los octetos sin cero inicial (3c:f:2:…), así que se normalizan.
if command -v nmap &>/dev/null; then
    log "Barrido ARP ${LAN_CIDR} (buscando los dispositivos en otra IP)…"
    nmap -sn -n "$LAN_CIDR" &>/dev/null || true
fi
moved="$(arp -an | grep -v incomplete \
    | awk '{ip=$2; mac=$4; n=split(mac,o,":"); m=""; for(i=1;i<=n;i++) m=m (i>1?":":"") sprintf("%02s",o[i]); gsub(/ /,"0",m); print ip, m}' \
    | grep -i '3c:0f:02' || true)"

echo ""
if [[ -n "$moved" ]]; then
    log "DIAGNÓSTICO: hay MACs IoT en la LAN pero en otra IP → DHCP/reservas del router:"
    echo "$moved"
    log "Acción: reservar la IP esperada por MAC en el router (docs/reservas-dhcp-bombillas-iot.md)."
else
    log "DIAGNÓSTICO: ${failed}/3 dispositivos 2,4 GHz ausentes de la LAN y sin MAC en otra IP."
    log "Causa probable: el radio 2,4 GHz del router (Movistar HGU) está colgado o cambió SSID/clave."
    log "Acción 1: reinicio COMPLETO del router (desenchufar 30 s, esperar ~3 min); reiniciar solo el Wi-Fi"
    log "  desde el portal no basta. Luego apagar/encender la lámpara y reconectar el USB-C del Satellite1."
    log "Acción 2 (si persiste, http://192.168.1.1): 2,4 GHz con el SSID/clave de ESPHome (HAOS"
    log "  /config/esphome/secrets.yaml → wifi_ssid/wifi_password); canal 1/6/11 fijo, 20 MHz, WPA2 personal,"
    log "  sin band-steering/«Smart WiFi». Relanza este script."
fi
exit 1
