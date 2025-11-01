#!/bin/bash
#
# Script de instalación para Raspberry Pi 4 (Audio Node)
# Configura Docker, PulseAudio, Bluetooth y Audio Service para captura de voz
#
# Uso:
#   chmod +x install_pi4.sh
#   ./install_pi4.sh
#
# Requisitos:
#   - Raspberry Pi OS 64-bit (Debian Bookworm recomendado)
#   - microSD con al menos 16GB
#   - Webcam USB con micrófono
#   - Altavoz Bluetooth (UE BOOM 2 o similar)
#   - Conexión a Internet
#   - Usuario con permisos sudo

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/tu-usuario/WayneHomeLab.git"
REPO_BRANCH="main"
INSTALL_DIR="/opt/charo"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script debe ejecutarse como root (usa sudo)"
        exit 1
    fi
}

check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        log_warn "No se detectó Raspberry Pi. ¿Continuar de todas formas? (y/n)"
        read -r response
        if [[ ! $response =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    log_info "Raspberry Pi detectada"
}

update_system() {
    log_info "Actualizando sistema..."
    apt-get update
    apt-get upgrade -y
    apt-get install -y \
        curl \
        git \
        vim \
        htop \
        ca-certificates \
        gnupg \
        lsb-release \
        alsa-utils \
        pulseaudio \
        pulseaudio-module-bluetooth \
        bluez \
        bluez-tools \
        bluetooth \
        python3-pip \
        python3-venv
}

install_docker() {
    log_info "Instalando Docker..."

    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc || true

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add current user to docker group
    if [ -n "${SUDO_USER:-}" ]; then
        usermod -aG docker "$SUDO_USER"
        log_info "Usuario $SUDO_USER agregado al grupo docker"
    fi

    # Enable and start Docker
    systemctl enable docker
    systemctl start docker

    log_info "Docker instalado correctamente"
    docker --version
}

setup_pulseaudio() {
    log_info "Configurando PulseAudio..."

    # Add user to audio group
    if [ -n "${SUDO_USER:-}" ]; then
        usermod -aG audio "$SUDO_USER"
    fi

    # Configure PulseAudio for system-wide mode (needed for Docker)
    mkdir -p /etc/pulse

    cat > /etc/pulse/system.pa <<'EOF'
#!/usr/bin/pulseaudio -nF
# System-wide PulseAudio configuration for Charo Audio Service

# Load modules
load-module module-native-protocol-unix auth-anonymous=1
load-module module-alsa-sink
load-module module-alsa-source device=hw:1,0  # USB Webcam
load-module module-bluetooth-discover
load-module module-bluetooth-policy

# Set default source to USB mic
set-default-source alsa_input.usb

# Automatic routing
load-module module-switch-on-connect
EOF

    # Create PulseAudio systemd service
    cat > /etc/systemd/system/pulseaudio.service <<'EOF'
[Unit]
Description=PulseAudio System Daemon
After=sound.target

[Service]
Type=notify
ExecStart=/usr/bin/pulseaudio --system --disallow-exit --disallow-module-loading=0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable pulseaudio
    systemctl start pulseaudio

    log_info "PulseAudio configurado correctamente"
}

setup_bluetooth() {
    log_info "Configurando Bluetooth..."

    # Enable Bluetooth service
    systemctl enable bluetooth
    systemctl start bluetooth

    # Make Bluetooth discoverable
    bluetoothctl power on
    bluetoothctl discoverable on
    bluetoothctl pairable on

    log_info "Bluetooth habilitado"
    log_info ""
    log_warn "ACCIÓN REQUERIDA: Empareja tu altavoz Bluetooth manualmente"
    log_warn "1. Pon el altavoz en modo emparejamiento"
    log_warn "2. Ejecuta: bluetoothctl"
    log_warn "3. En bluetoothctl, ejecuta: scan on"
    log_warn "4. Cuando veas tu altavoz, ejecuta: pair [MAC_ADDRESS]"
    log_warn "5. Luego: trust [MAC_ADDRESS]"
    log_warn "6. Finalmente: connect [MAC_ADDRESS]"
    log_warn ""
    log_warn "Presiona ENTER cuando hayas emparejado el altavoz..."
    read -r
}

detect_audio_devices() {
    log_info "Detectando dispositivos de audio..."

    log_info "Tarjetas de sonido disponibles:"
    aplay -l

    log_info ""
    log_info "Dispositivos de entrada (micrófonos):"
    arecord -l

    log_info ""
    log_info "Fuentes PulseAudio:"
    sudo -u "$SUDO_USER" pactl list short sources

    log_info ""
    log_info "Sumideros PulseAudio:"
    sudo -u "$SUDO_USER" pactl list short sinks
}

test_microphone() {
    log_info "Probando micrófono..."

    log_warn "Grabando 5 segundos de audio de prueba..."
    log_warn "Habla algo cerca del micrófono de la webcam..."

    sudo -u "$SUDO_USER" arecord -D plughw:1,0 -f cd -d 5 /tmp/test_recording.wav

    log_info "Reproduciendo grabación..."
    sudo -u "$SUDO_USER" aplay /tmp/test_recording.wav

    log_warn "¿Se escuchó correctamente la grabación? (y/n)"
    read -r response
    if [[ ! $response =~ ^[Yy]$ ]]; then
        log_error "Problema con el micrófono. Verifica la conexión de la webcam USB"
        exit 1
    fi

    log_info "Micrófono funcionando correctamente"
}

clone_repository() {
    log_info "Clonando repositorio..."

    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    if [ -d ".git" ]; then
        log_info "Repositorio ya existe, actualizando..."
        git pull origin "$REPO_BRANCH"
    else
        log_info "Clonando repositorio desde $REPO_URL..."
        git clone -b "$REPO_BRANCH" "$REPO_URL" .
    fi

    log_info "Repositorio clonado en $INSTALL_DIR"
}

setup_environment() {
    log_info "Configurando entorno..."

    cd "$INSTALL_DIR"

    # Copy example env files if they don't exist
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "Archivo .env creado desde .env.example"
            log_warn "IMPORTANTE: Edita $INSTALL_DIR/.env con tus valores reales"
        else
            log_error "No se encontró .env.example"
            exit 1
        fi
    fi

    log_info "Entorno configurado"
}

build_services() {
    log_info "Construyendo servicios Docker..."

    cd "$INSTALL_DIR/deployment/docker"

    # Build audio-service
    log_info "Construyendo audio-service..."
    docker compose -f pi4-compose.yml build audio-service

    log_info "Servicios construidos correctamente"
}

start_services() {
    log_info "Iniciando servicios..."

    cd "$INSTALL_DIR/deployment/docker"

    # Start audio service
    docker compose -f pi4-compose.yml up -d

    log_info "Servicios iniciados correctamente"
    log_info "Puedes verificar el estado con: docker compose -f pi4-compose.yml ps"
}

configure_systemd_service() {
    log_info "Configurando servicio systemd para auto-inicio..."

    cat > /etc/systemd/system/charo-audio.service <<EOF
[Unit]
Description=Charo Voice Assistant - Audio Service (Pi4)
Requires=docker.service pulseaudio.service bluetooth.service
After=docker.service pulseaudio.service bluetooth.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR/deployment/docker
ExecStart=/usr/bin/docker compose -f pi4-compose.yml up -d
ExecStop=/usr/bin/docker compose -f pi4-compose.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable charo-audio.service

    log_info "Servicio systemd configurado. Se iniciará automáticamente en el próximo boot"
}

print_next_steps() {
    log_info ""
    log_info "=============================================="
    log_info "    INSTALACIÓN COMPLETADA CON ÉXITO"
    log_info "=============================================="
    log_info ""
    log_info "Próximos pasos:"
    log_info ""
    log_info "1. Edita las variables de entorno:"
    log_info "   $INSTALL_DIR/.env"
    log_info "   - Configura CHARO_CORE_HOST con la IP de la Pi5"
    log_info "   - Configura BLUETOOTH_MAC con la MAC de tu altavoz"
    log_info ""
    log_info "2. Verifica que el servicio esté corriendo:"
    log_info "   cd $INSTALL_DIR/deployment/docker"
    log_info "   docker compose -f pi4-compose.yml ps"
    log_info ""
    log_info "3. Verifica logs del servicio:"
    log_info "   docker compose -f pi4-compose.yml logs -f audio-service"
    log_info ""
    log_info "4. Prueba el wake word diciendo: 'Oye, Charo'"
    log_info ""
    log_info "5. Para reiniciar, cierra la sesión y vuelve a iniciarla"
    log_info "   (necesario para aplicar permisos de audio y docker)"
    log_info ""
    log_info "=============================================="
}

# Main execution
main() {
    log_info "Iniciando instalación de Proyecto Charo Audio Service en Raspberry Pi 4..."

    check_root
    check_raspberry_pi
    update_system
    install_docker
    setup_pulseaudio
    setup_bluetooth
    detect_audio_devices
    test_microphone
    clone_repository
    setup_environment
    build_services
    start_services
    configure_systemd_service
    print_next_steps

    log_info "¡Instalación completada!"
}

main "$@"
