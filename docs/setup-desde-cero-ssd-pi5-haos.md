# Guía completa desde cero (SSD) — Raspberry Pi 5 + Proxmox + Home Assistant OS

Esta guía está pensada para cuando el nodo quedó inaccesible por red y quieres rehacer todo desde cero en un SSD, sin depender de estado previo.

## Objetivo final

- Raspberry Pi 5 arrancando desde SSD.
- Acceso SSH estable al host.
- Proxmox instalado.
- VM de Home Assistant OS creada y arrancada.
- Home Assistant accesible por web.

## Requisitos previos

- Mac con este repo clonado en: `/Users/miguel/Proyectos/WayneHomeLab`
- SSD conectado al Mac para flasheo
- Raspberry Pi 5 conectada por Ethernet al router
- Reserva DHCP recomendada en el router:
  - Host Pi5: `192.168.1.100`
  - VM HAOS: `192.168.1.110`

---

## 1) Formatear y flashear el SSD con Raspberry Pi Imager (macOS Tahoe 26.4.1)

1. Conecta el SSD al Mac.
2. Abre **Raspberry Pi Imager**.
3. Selecciona:
  - **Raspberry Pi Device**: Raspberry Pi 5
  - **Operating System**: Raspberry Pi OS Lite (64-bit)
  - **Storage**: tu SSD
4. Pulsa **Next** y entra en **Edit Settings**.
5. Configura en **General**:
  - Hostname: `waynelab-core`
  - Username: `pi`
  - Password: (elige una temporal fuerte)
  - Configure wireless LAN: desactivado (si usarás Ethernet)
  - Locale/Timezone: tu configuración real
6. Configura en **Services**:
  - Enable SSH: activado
  - Use password authentication: activado (solo bootstrap inicial)
7. Guarda y pulsa **Write**.
8. Al terminar, expulsa el SSD de forma segura y conéctalo a la Raspberry Pi 5.

---

## 2) Primer arranque y acceso SSH

1. Conecta Pi5 por Ethernet.
2. Enciende y espera 60-120 segundos.
3. Prueba SSH:

```bash
ssh pi@192.168.1.100
```

Si no responde, revisa en router la IP asignada y usa esa IP.

---

## 3) Bootstrap del host (script del repo)

Desde el Mac:

```bash
cd /Users/miguel/Proyectos/WayneHomeLab

scp infrastructure/nodes/core/setup_host.sh pi@192.168.1.100:/tmp/
scp infrastructure/nodes/core/sysctl.conf pi@192.168.1.100:/tmp/
ssh -t pi@192.168.1.100 "sudo bash /tmp/setup_host.sh"
ssh -t pi@192.168.1.100 "sudo reboot"
```

Espera 1-2 minutos y valida de nuevo:

```bash
ssh pi@192.168.1.100 "hostname; ip -br a"
```

---

## 4) Instalación de Proxmox (instrucciones literales de PXVIRT)

**IMPORTANTE:** A continuación se copian literalmente los pasos publicados en:
`https://docs.pxvirt.lierfang.com/en/installfromdebian.html`

### 4.1 System Requirements

```
PXVIRT 8 -> Debian 12 Bookworm / Armbian Bookworm

Other systems based on Debian-Bookworm can also be used for installation.

Ubuntu is NOT supported!
```

### 4.2 Installation Preparation

```
1. Add Software Repository

Download GPG key

curl -L https://mirrors.lierfang.com/pxcloud/lierfang.gpg -o /etc/apt/trusted.gpg.d/lierfang.gpg

Add the repository to the sources list

source /etc/os-release
echo "deb  https://mirrors.lierfang.com/pxcloud/pxvirt $VERSION_CODENAME main">/etc/apt/sources.list.d/pxvirt-sources.list
```

```
1. Modify Hostname

Proxmox-VE services need to resolve IP addresses using hostname. We need to configure the correct hostname.

Assuming your current IP is 10.10.10.10 and hostname is pxvirt

Modify the /etc/hosts file

127.0.0.1   localhost
# Add hostname information below
10.10.10.10 pxvirt.local pxvirt 

::1         localhost ip6-localhost ip6-loopback
fe00::0     ip6-localnet
ff00::0     ip6-mcastprefix
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
```

### 4.3 Install ifupdown2 (Skip if already installed)

```
PVE uses`ifupdown2` for network configuration. Some distributions might have installed`NetworkManager`, so we need to disable its service.

systemctl disable NetworkManager
systemctl stop NetworkManager
```

```
Then execute the commands

apt update
apt install ifupdown2 -y
rm /etc/network/interfaces.new
```

```
Configure static IP using ifupdown2. You can check your network interface using`ip link show`

root@nas:~# ip link show
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: enp5s0f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq master vmbr0 state UP mode DEFAULT group default qlen 1000
    link/ether d0:50:99:d1:13:02 brd ff:ff:ff:ff:ff:ff
4: enp5s0f1: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
    link/ether d0:50:99:d1:13:03 brd ff:ff:ff:ff:ff:ff
```

```
Assuming the network interface is`enp5s0f0`

# Edit /etc/network/interfaces
nano /etc/network/interfaces
# Enter the following information
auto enp5s0f0
iface enp5s0f0 inet static
      address 10.13.14.109/24
      gateway 10.13.14.254
```

```
reload network

If your network configuration is incorrect, a restart may prevent remote access. Ensure that you have connected a monitor or a serial cable.

Then restart the machine to ensure the network is properly applied. If the network configuration is incorrect, it might cause installation interruption due to network disconnection, making the machine inaccessible remotely.
```

### 4.4 Install PXVIRT

```
apt update
apt install proxmox-ve pve-manager qemu-server pve-cluster
```

### 4.5 Create Network Bridge

```
After installation, log in to the web interface at`https://your_ip:8006`. The username is`root`, and the password is your`root` password. Make sure to select`Linux PAM` as the realm.

After logging in, go to the network settings page, delete the original network interface IP, and create a`Linux Bridge`.

The installation is now complete.
```

---

## 4.6 Adaptación de los pasos anteriores a tu red real

La sección 4.1-4.5 se mantiene literal por tu requisito. Para ejecutarla en tu entorno, usa estos valores reales:

- IP del host: `192.168.1.100`
- Hostname: `waynelab-core`
- Dominio local recomendado: `waynelab-core.local`

Cuando edites `/etc/hosts`, la línea práctica para tu caso es:

```text
192.168.1.100 waynelab-core.local waynelab-core
```

Y cuando la guía literal hable de IP estática/gateway, sustitúyelo por tu red real (ejemplo típico):

```text
address 192.168.1.100/24
gateway 192.168.1.1
```

Para no perder acceso SSH durante la migración de red:

- Haz los cambios dentro de una sesión SSH activa.
- Antes de reiniciar, valida sintaxis:
  - `ifquery --list`
  - `ifreload -a` (si aplica)
- Reinicia solo cuando confirmes que `ip a` y `ip r` muestran `192.168.1.100`.

---

## 5) Validación de Proxmox tras reinicio

Desde el Mac:

```bash
ssh root@192.168.1.100 "pveversion -v | head -n 20"
ssh root@192.168.1.100 "systemctl is-active pve-cluster pvedaemon pveproxy pvestatd"
nc -zv 192.168.1.100 8006
```

Abre en navegador:

- `https://192.168.1.100:8006`
- Usuario: `root`
- Realm: `Linux PAM`

---

## 6) Crear VM Home Assistant OS

Desde el repo en el Mac:

```bash
cd /Users/miguel/Proyectos/WayneHomeLab

scp infrastructure/proxmox/create_haos_vm.sh root@192.168.1.100:/tmp/
ssh root@192.168.1.100 "chmod +x /tmp/create_haos_vm.sh && VMID=100 BRIDGE=vmbr0 bash /tmp/create_haos_vm.sh"
ssh root@192.168.1.100 "qm status 100 && qm list"
```

Espera 5-10 minutos y valida HA:

```bash
nc -zv 192.168.1.110 8123
```

Luego abre:

- `http://192.168.1.110:8123`

---

## 7) Cargar configuración base de Home Assistant

Una vez hecho el onboarding inicial en HA e instalado el add-on Terminal/SSH:

```bash
scp home-assistant/configuration.yaml root@192.168.1.110:/config/
scp -r home-assistant/includes root@192.168.1.110:/config/
scp home-assistant/secrets.yaml.example root@192.168.1.110:/config/secrets.yaml
ssh root@192.168.1.110 "ha core restart && ha core info"
```

Rellena `/config/secrets.yaml` con tus valores reales (API key, latitud/longitud, URLs).

---

## 8) Checklist final

- SSH al host Pi5 (`192.168.1.100`) funciona.
- Proxmox web en `aho` responde.
- VM `100` está en `running`.
- Home Assistant en `http://192.168.1.110:8123` responde.
- Configuración base de `home-assistant/` copiada en `/config`.

## 9) Siguiente (DNS + acceso remoto)

Tras HAOS estable, despliega las otras VMs del lab:

1. Pi-hole (VMID 101 / `.53`) — [pihole.md](pihole.md)
2. WireGuard + Caddy (VMID 102 / `.55`) — [wireguard.md](wireguard.md)

Path headless completo (edge RPi 3b incluido): [setup-from-scratch-headless.md](setup-from-scratch-headless.md).

