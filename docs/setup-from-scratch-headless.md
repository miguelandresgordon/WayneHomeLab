# Setup From Scratch (Headless)

This guide is the canonical path to rebuild WayneHomeLab from zero using a MacBook, a Raspberry Pi 5, and a Raspberry Pi 3 Model B.

## Target Outcome

- Pi5 boots from USB SSD (no monitor/keyboard required)
- Proxmox runs on Pi5
- Home Assistant OS runs inside a VM with dedicated LAN IP
- Pi3 runs DietPi as auxiliary/backup node
- Remote access works through WireGuard on `vpn.waynehomelab.com`

## 0) Planning and Reservations

Reserve these DHCP leases in your router:

- `192.168.1.100` -> Pi5 host (`waynelab-core`)
- `192.168.1.110` -> HAOS VM (`homeassistant`)
- `192.168.1.101` -> Pi3 edge (`waynelab-edge`)

Create DNS record:

- `vpn.waynehomelab.com` -> your public IPv4

Router port forward:

- UDP `51820` -> `192.168.1.100:51820`

## 1) Pi5 SSD Boot (Headless)

From your MacBook, flash Raspberry Pi OS Lite 64-bit to the USB SSD and preconfigure SSH:

```bash
bash infrastructure/provisioning/mac/flash_rpi_os_lite_ssd.sh \
  --target /dev/diskX \
  --hostname waynelab-core \
  --username pi \
  --password 'CHANGE_ME'
```

Then:

1. Connect SSD to Pi5
2. Connect Pi5 to Ethernet
3. Power on and wait 60-90 seconds
4. Validate SSH:

```bash
ssh pi@192.168.1.100
```

Run host bootstrap:

```bash
scp infrastructure/nodes/core/setup_host.sh pi@192.168.1.100:/tmp/
scp infrastructure/nodes/core/sysctl.conf pi@192.168.1.100:/tmp/
ssh pi@192.168.1.100 "sudo bash /tmp/setup_host.sh && sudo reboot"
```

## 2) Proxmox + HAOS VM

Install Proxmox community port on Pi5 (latest supported method).

After Proxmox is running:

```bash
scp infrastructure/proxmox/create_haos_vm.sh root@192.168.1.100:/tmp/
ssh root@192.168.1.100 "BRIDGE=vmbr0 VMID=100 bash /tmp/create_haos_vm.sh"
```

Important:

- HAOS VM must use its own LAN IP (`192.168.1.110`), not the host IP.
- Access HA using `http://192.168.1.110:8123`.

## 3) Pi3 Auxiliary Node (Headless)

Flash DietPi and optionally preseed `dietpi.txt`:

```bash
cp infrastructure/nodes/edge/dietpi.txt /Volumes/bootfs/dietpi.txt
```

Boot Pi3 and run:

```bash
scp infrastructure/nodes/edge/setup_edge.sh dietpi@192.168.1.101:/tmp/
ssh dietpi@192.168.1.101 "sudo SSD_DEVICE=/dev/sda1 bash /tmp/setup_edge.sh"
```

Configure Pi3 as backup sink:

```bash
scp infrastructure/nodes/edge/setup_backup_sink.sh dietpi@192.168.1.101:/tmp/
ssh dietpi@192.168.1.101 "sudo BACKUP_MOUNT=/mnt/ssd bash /tmp/setup_backup_sink.sh"
```

Use Pi3 as backup sink and optional lightweight voice services.

## 4) WireGuard on Pi5

Install server:

```bash
scp infrastructure/nodes/core/install_wireguard.sh root@192.168.1.100:/tmp/
ssh root@192.168.1.100 "WG_ENDPOINT=vpn.waynehomelab.com bash /tmp/install_wireguard.sh"
```

Create peer profiles (MacBook/iPhone):

```bash
scp infrastructure/nodes/core/create_wireguard_peer.sh root@192.168.1.100:/tmp/
ssh root@192.168.1.100 "bash /tmp/create_wireguard_peer.sh macbook"
ssh root@192.168.1.100 "bash /tmp/create_wireguard_peer.sh iphone"
```

Download peer config and import into WireGuard app.

## 5) Home Assistant Configuration Baseline

In HA (`http://192.168.1.110:8123`):

1. Complete onboarding
2. Set internal URL to `http://192.168.1.110:8123`
3. Configure ESPHome, Satellite1, and Wyoming integrations
4. Verify TTS/STT path if voice services are enabled on Pi3

## 6) Backup and Recovery Baseline

- Proxmox VM snapshots scheduled on Pi5
- Home Assistant backups copied to Pi3 storage
- Test restore once before production use

## Validation Checklist

- Pi5 reachable by SSH and Proxmox UI
- HAOS reachable at `192.168.1.110:8123`
- Pi3 reachable by SSH and mounted SSD
- WireGuard tunnel works from mobile network
- HA accessible over VPN without exposing HA directly to the internet
