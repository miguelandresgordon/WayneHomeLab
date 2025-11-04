#!/bin/bash
#
# Script de formateo automático para HDD en Raspberry Pi 3/4
# Formatea un disco externo y lo configura para auto-montaje en /mnt/hdd
#
# Uso:
#   chmod +x format_hdd.sh
#   sudo ./format_hdd.sh
#
# ADVERTENCIA: Esto borrará TODOS los datos del disco especificado

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check root
if [[ $EUID -ne 0 ]]; then
    log_error "Este script debe ejecutarse como root (usa sudo)"
    exit 1
fi

echo ""
echo "=================================================="
echo "  FORMATEO DE HDD PARA RASPBERRY PI 3/4"
echo "=================================================="
echo ""

# Detect HDD
log_step "1. Detectando discos externos..."
lsblk -d -n -o NAME,SIZE,TYPE,TRAN | grep usb

echo ""
if [ ! -b /dev/sda ]; then
    log_error "No se detectó disco externo en /dev/sda"
    log_info "Discos disponibles:"
    lsblk
    exit 1
fi

log_info "Disco detectado: /dev/sda"
HDD_SIZE=$(lsblk -d -n -o SIZE /dev/sda)
log_info "Tamaño: $HDD_SIZE"

echo ""
log_step "2. Información del disco a formatear:"
sudo fdisk -l /dev/sda | grep "Disk /dev/sda"

echo ""
log_warn "⚠️  ADVERTENCIA ⚠️"
log_warn "Esto BORRARÁ COMPLETAMENTE todos los datos en /dev/sda ($HDD_SIZE)"
log_warn "¿Estás ABSOLUTAMENTE seguro?"
log_warn ""
log_warn "Escribe exactamente 'SI BORRAR TODO' para continuar:"
read -r respuesta

if [ "$respuesta" != "SI BORRAR TODO" ]; then
    log_info "Cancelado por el usuario"
    exit 0
fi

echo ""
log_step "3. Desmontando particiones existentes..."
sudo umount /dev/sda* 2>/dev/null || true
log_info "Particiones desmontadas"

echo ""
log_step "4. Creando nueva tabla de particiones GPT..."
sudo parted -s /dev/sda mklabel gpt
log_info "Tabla de particiones GPT creada"

echo ""
log_step "5. Creando partición primaria..."
sudo parted -s /dev/sda mkpart primary ext4 0% 100%
log_info "Partición creada"

echo ""
log_step "6. Esperando a que el sistema detecte la partición..."
sleep 3
log_info "Partición detectada"

echo ""
log_step "7. Formateando a ext4..."
sudo mkfs.ext4 -F /dev/sda1 << EOF
y
EOF
log_info "Formato ext4 completado"

echo ""
log_step "8. Creando punto de montaje..."
sudo mkdir -p /mnt/hdd
log_info "Punto de montaje creado: /mnt/hdd"

echo ""
log_step "9. Montando el disco..."
sudo mount /dev/sda1 /mnt/hdd
log_info "Disco montado"

echo ""
log_step "10. Configurando permisos..."
sudo chown -R $SUDO_USER:$SUDO_USER /mnt/hdd
sudo chmod 755 /mnt/hdd
log_info "Permisos configurados"

echo ""
log_step "11. Obteniendo UUID para auto-montaje..."
UUID=$(sudo blkid -s UUID -o value /dev/sda1)
log_info "UUID del disco: $UUID"

echo ""
log_step "12. Configurando auto-montaje en /etc/fstab..."
if grep -q "$UUID" /etc/fstab; then
    log_warn "Ya existe una entrada con este UUID en /etc/fstab"
    log_warn "Saltando configuración de fstab"
else
    echo "UUID=$UUID /mnt/hdd ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab > /dev/null
    log_info "Entrada añadida a /etc/fstab"
fi

echo ""
log_step "13. Verificando configuración..."
echo ""
echo "Estado del montaje:"
df -h /mnt/hdd
echo ""
echo "Contenido del directorio:"
ls -la /mnt/hdd
echo ""

echo "=================================================="
log_info "✅ FORMATEO COMPLETADO EXITOSAMENTE"
echo "=================================================="
echo ""
log_info "El HDD está listo para usar en: /mnt/hdd"
log_info "Tamaño disponible: $(df -h /mnt/hdd | tail -1 | awk '{print $4}')"
echo ""
log_info "Próximos pasos:"
log_info "1. El disco se montará automáticamente al arrancar"
log_info "2. Puedes verificar con: df -h"
log_info "3. Los datos se guardarán en /mnt/hdd"
echo ""
log_info "Para probar el auto-montaje, ejecuta:"
log_info "  sudo umount /mnt/hdd"
log_info "  sudo mount -a"
log_info "  df -h | grep hdd"
echo ""
