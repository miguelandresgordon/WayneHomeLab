#!/bin/bash
#
# Script de configuración de Bluetooth para Raspberry Pi 4
# Ayuda a emparejar y configurar el altavoz Bluetooth UE BOOM 2
#
# Uso:
#   chmod +x setup_bluetooth.sh
#   ./setup_bluetooth.sh
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if running with sudo
if [[ $EUID -ne 0 ]]; then
    echo "Este script necesita permisos sudo para configurar Bluetooth"
    exit 1
fi

log_info "Configuración de Bluetooth para Charo Audio Service"
log_info "=================================================="
log_info ""

# Enable Bluetooth
log_info "Habilitando Bluetooth..."
systemctl enable bluetooth
systemctl start bluetooth

# Power on Bluetooth
bluetoothctl power on

# Make discoverable
bluetoothctl discoverable on
bluetoothctl pairable on

log_info ""
log_warn "INSTRUCCIONES PARA EMPAREJAR EL ALTAVOZ:"
log_warn "1. Pon tu altavoz Bluetooth en modo emparejamiento"
log_warn "   (Para UE BOOM 2: Mantén presionado el botón Bluetooth hasta que escuches el tono)"
log_warn ""
log_warn "2. Presiona ENTER para comenzar el escaneo..."
read -r

log_info "Escaneando dispositivos Bluetooth (15 segundos)..."

# Scan for devices in the background
timeout 15 bluetoothctl --timeout 15 scan on > /tmp/bt_scan.log 2>&1 &
SCAN_PID=$!

# Wait for scan to complete
sleep 15

# Stop scan
bluetoothctl scan off > /dev/null 2>&1 || true

log_info ""
log_info "Dispositivos encontrados:"
bluetoothctl devices

log_info ""
log_warn "Ingresa la dirección MAC del dispositivo que deseas emparejar"
log_warn "(Ejemplo: 88:C6:26:XX:XX:XX para UE BOOM 2)"
read -p "MAC Address: " MAC_ADDRESS

if [ -z "$MAC_ADDRESS" ]; then
    log_warn "No se ingresó ninguna dirección MAC. Saliendo..."
    exit 1
fi

# Pair device
log_info "Emparejando con $MAC_ADDRESS..."
bluetoothctl pair "$MAC_ADDRESS"

# Trust device
log_info "Confiando en el dispositivo..."
bluetoothctl trust "$MAC_ADDRESS"

# Connect device
log_info "Conectando al dispositivo..."
bluetoothctl connect "$MAC_ADDRESS"

# Verify connection
sleep 2
if bluetoothctl info "$MAC_ADDRESS" | grep -q "Connected: yes"; then
    log_info "✓ Dispositivo conectado correctamente!"
else
    log_warn "El dispositivo no se pudo conectar automáticamente"
    log_warn "Intenta conectar manualmente con: bluetoothctl connect $MAC_ADDRESS"
fi

# Configure PulseAudio Bluetooth module
log_info "Configurando PulseAudio para Bluetooth..."
sudo -u "${SUDO_USER:-$USER}" pactl load-module module-bluetooth-discover

log_info ""
log_info "Dispositivos de audio disponibles:"
sudo -u "${SUDO_USER:-$USER}" pactl list short sinks

log_info ""
log_info "=================================================="
log_info "Configuración completada!"
log_info "=================================================="
log_info ""
log_info "MAC Address del dispositivo: $MAC_ADDRESS"
log_info ""
log_info "Agrega esta MAC a tu archivo .env:"
log_info "BLUETOOTH_MAC=$MAC_ADDRESS"
log_info "BLUETOOTH_DEVICE_NAME=\"UE BOOM 2\""
log_info ""
log_info "Para reconectar en el futuro:"
log_info "  bluetoothctl connect $MAC_ADDRESS"
log_info ""
log_info "Para verificar conexión:"
log_info "  bluetoothctl info $MAC_ADDRESS"
log_info ""
