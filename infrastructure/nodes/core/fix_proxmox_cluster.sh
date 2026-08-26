#!/usr/bin/env bash
# Fix pve-cluster "Connection refused" when hostname resolves to 127.0.1.1
# (cloud-init manage_etc_hosts overwrites /etc/hosts on reboot).
set -euo pipefail

HOST_IP="${HOST_IP:-192.168.1.100}"
HOSTNAME="${HOSTNAME:-waynelab-core}"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run as root: sudo bash $0"
    exit 1
fi

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Disabling cloud-init manage_etc_hosts..."
sed -i 's/^manage_etc_hosts:.*/manage_etc_hosts: false/' /etc/cloud/cloud.cfg

log "Writing /etc/hosts (${HOST_IP} -> ${HOSTNAME})..."
cat > /etc/hosts <<EOF
127.0.0.1 localhost
${HOST_IP} ${HOSTNAME}.local ${HOSTNAME}

::1 localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF

log "Restarting Proxmox services..."
systemctl restart pve-cluster
sleep 2
systemctl restart pvestatd pvedaemon pveproxy

log "Verification:"
getent hosts "${HOSTNAME}"
systemctl is-active pve-cluster pvestatd pvedaemon pveproxy
