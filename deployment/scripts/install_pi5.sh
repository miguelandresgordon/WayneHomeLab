#!/bin/bash
#
# Script de instalación para Raspberry Pi 5 (Main Node)
# Configura Docker, servicios de Charo Core, Home Assistant, PostgreSQL, Redis y Piper TTS
#
# Uso:
#   chmod +x install_pi5.sh
#   ./install_pi5.sh
#
# Requisitos:
#   - Raspberry Pi OS 64-bit (Debian Bookworm recomendado)
#   - SSD conectado vía USB 3.0
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
SSD_MOUNT_POINT="/mnt/ssd"
SSD_DEVICE="/dev/sda1"  # Ajustar según tu SSD

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
        rsync \
        parted \
        e2fsprogs
}

setup_ssd() {
    log_info "Configurando SSD externo..."

    # Check if SSD exists
    if [ ! -b "$SSD_DEVICE" ]; then
        log_warn "No se encontró SSD en $SSD_DEVICE"
        log_warn "Dispositivos disponibles:"
        lsblk
        log_warn "¿Deseas continuar sin SSD? (y/n)"
        read -r response
        if [[ $response =~ ^[Yy]$ ]]; then
            log_warn "Continuando sin SSD. Los datos se guardarán en la SD"
            return 0
        else
            exit 1
        fi
    fi

    # Create mount point
    mkdir -p "$SSD_MOUNT_POINT"

    # Format SSD (ADVERTENCIA: Esto borrará todos los datos del SSD)
    log_warn "¿Deseas formatear el SSD en $SSD_DEVICE? Esto BORRARÁ todos los datos. (y/n)"
    read -r response
    if [[ $response =~ ^[Yy]$ ]]; then
        log_info "Formateando SSD..."
        mkfs.ext4 -F "$SSD_DEVICE"
    fi

    # Mount SSD
    log_info "Montando SSD..."
    mount "$SSD_DEVICE" "$SSD_MOUNT_POINT"

    # Add to fstab for auto-mount on boot
    if ! grep -q "$SSD_DEVICE" /etc/fstab; then
        log_info "Agregando SSD a /etc/fstab para auto-mount..."
        SSD_UUID=$(blkid -s UUID -o value "$SSD_DEVICE")
        echo "UUID=$SSD_UUID $SSD_MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
    fi

    log_info "SSD configurado correctamente en $SSD_MOUNT_POINT"
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

clone_repository() {
    log_info "Clonando repositorio..."

    # Create install directory on SSD if available, otherwise on SD
    if mountpoint -q "$SSD_MOUNT_POINT"; then
        INSTALL_DIR="$SSD_MOUNT_POINT/charo"
    else
        log_warn "SSD no montado, usando /opt/charo en SD"
    fi

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

    # Copy Home Assistant secrets
    if [ ! -f "services/home-assistant/config/secrets.yaml" ]; then
        if [ -f "services/home-assistant/config/secrets.yaml.example" ]; then
            cp services/home-assistant/config/secrets.yaml.example services/home-assistant/config/secrets.yaml
            log_warn "Archivo secrets.yaml creado desde secrets.yaml.example"
            log_warn "IMPORTANTE: Edita $INSTALL_DIR/services/home-assistant/config/secrets.yaml con tus valores reales"
        fi
    fi

    log_info "Entorno configurado"
}

setup_docker_data_on_ssd() {
    if mountpoint -q "$SSD_MOUNT_POINT"; then
        log_info "Configurando Docker para usar SSD..."

        # Stop Docker
        systemctl stop docker

        # Create Docker data directory on SSD
        mkdir -p "$SSD_MOUNT_POINT/docker"

        # Backup existing Docker data if any
        if [ -d "/var/lib/docker" ]; then
            log_info "Respaldando datos de Docker existentes..."
            rsync -aP /var/lib/docker/ "$SSD_MOUNT_POINT/docker/"
        fi

        # Configure Docker to use SSD
        mkdir -p /etc/docker
        cat > /etc/docker/daemon.json <<EOF
{
  "data-root": "$SSD_MOUNT_POINT/docker"
}
EOF

        # Start Docker
        systemctl start docker

        log_info "Docker configurado para usar SSD"
    else
        log_warn "SSD no disponible, Docker usará almacenamiento por defecto"
    fi
}

build_services() {
    log_info "Construyendo servicios Docker..."

    cd "$INSTALL_DIR/deployment/docker"

    # Build charo-core service
    log_info "Construyendo charo-core..."
    docker compose -f pi5-compose.yml build charo-core

    log_info "Servicios construidos correctamente"
}

start_services() {
    log_info "Iniciando servicios..."

    cd "$INSTALL_DIR/deployment/docker"

    # Start all services
    docker compose -f pi5-compose.yml up -d

    log_info "Servicios iniciados correctamente"
    log_info "Puedes verificar el estado con: docker compose -f pi5-compose.yml ps"
}

configure_systemd_service() {
    log_info "Configurando servicio systemd para auto-inicio..."

    cat > /etc/systemd/system/charo.service <<EOF
[Unit]
Description=Charo Voice Assistant - Pi5 Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR/deployment/docker
ExecStart=/usr/bin/docker compose -f pi5-compose.yml up -d
ExecStop=/usr/bin/docker compose -f pi5-compose.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable charo.service

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
    log_info ""
    log_info "2. Configura Home Assistant secrets:"
    log_info "   $INSTALL_DIR/services/home-assistant/config/secrets.yaml"
    log_info ""
    log_info "3. Verifica que los servicios estén corriendo:"
    log_info "   cd $INSTALL_DIR/deployment/docker"
    log_info "   docker compose -f pi5-compose.yml ps"
    log_info ""
    log_info "4. Accede a Home Assistant:"
    log_info "   http://$(hostname -I | awk '{print $1}'):8123"
    log_info ""
    log_info "5. Verifica logs de servicios:"
    log_info "   docker compose -f pi5-compose.yml logs -f"
    log_info ""
    log_info "6. Para reiniciar, cierra la sesión y vuelve a iniciarla"
    log_info "   (necesario para aplicar permisos del grupo docker)"
    log_info ""
    log_info "=============================================="
}

# Main execution
main() {
    log_info "Iniciando instalación de Proyecto Charo en Raspberry Pi 5..."

    check_root
    check_raspberry_pi
    update_system
    setup_ssd
    install_docker
    setup_docker_data_on_ssd
    clone_repository
    setup_environment
    build_services
    start_services
    configure_systemd_service
    print_next_steps

    log_info "¡Instalación completada!"
}

main "$@"
