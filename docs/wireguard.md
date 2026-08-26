# WireGuard VM + HTTPS privado (Home Assistant)

Acceso remoto a Home Assistant en **`https://ha.waynehomelab.com`** solo con VPN activa.  
HA **no** se expone a Internet (ni 80, ni 443, ni 8123 en el router).

| Campo | Valor |
|-------|--------|
| Host | `waynelab-core` `192.168.1.100` (PXVIRT / Debian 13, ~8 GB) |
| VMID | `102` (`onboot=1`, `startup order=2`) |
| Hostname guest | `wireguard` |
| Guest OS | Debian 12 (bookworm) cloud image ARM64 |
| IP LAN | `192.168.1.55/24` (`.54` estaba en conflicto con otro host MAC `7e:9b:d8:fa:86:f8`) |
| MAC `net0` | `bc:24:11:e9:6c:c9` |
| VPN subnet | `10.44.0.0/24` (server `10.44.0.1`) |
| Endpoint | `vpn.waynehomelab.com:51820/udp` |
| Recursos | 1 vCPU, **512 MiB** RAM, balloon 128, disco **4G** (`local`) |
| HTTPS | Caddy en `10.44.0.1:443` → `http://192.168.1.110:8123` |
| TLS | Let’s Encrypt **DNS-01** vía **Cloudflare** (sin abrir 80/443) |
| DNS split | Pi-hole: `ha.waynehomelab.com` → `10.44.0.1` |

Referencias:

- [Let’s Encrypt DNS-01](https://letsencrypt.org/docs/challenge-types/)
- [Caddy bind](https://caddyserver.com/docs/caddyfile/directives/bind) · [Cloudflare module](https://github.com/caddy-dns/cloudflare)
- [Cloudflare API tokens](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
- [HA reverse proxies](https://www.home-assistant.io/integrations/http/#reverse-proxies)
- [WireGuard](https://www.wireguard.com/) · [Proxmox memory](https://pve.proxmox.com/wiki/Qemu/KVM_Virtual_Machines#qm_memory)

---

## 0) Presupuesto RAM (RPi 5 ~8 GB)

Dejar **~1 GB** al host Proxmox.

| VM | MiB |
|----|-----|
| HAOS 100 | 4096 |
| Pi-hole 101 | 768 (mín. oficial 512) |
| WireGuard 102 | 512 |
| Host (aprox.) | resto (~2.8 GB si suma VMs = 5376) |

Tras crear la VM:

```bash
ssh -t pi@192.168.1.100 'free -h; sudo qm list'
```

Si el host queda **&lt; 500 MiB** disponibles:

```bash
ssh -t pi@192.168.1.100 'sudo qm set 101 --memory 512'
```

Actualiza entonces `docs/pihole.md` y `infrastructure/proxmox/pihole.conf`.

---

## 1) DNS (`waynehomelab.com`)

- **Registrar:** Porkbun (compra / renovación).
- **Autoritativo:** Cloudflare (`monika.ns.cloudflare.com` / `syeef.ns.cloudflare.com`).  
  ACME DNS-01 y el registro `vpn` van en **Cloudflare**, no en la API de Porkbun.

Registros públicos en Cloudflare (**Solo DNS**, nube gris):

1. `A vpn.waynehomelab.com` → IP WAN del router (`2.139.17.245` en el lab).  
   Si el WAN es DHCP, usa DDNS del router o un updater hacia Cloudflare. Si hay **CGNAT**, el handshake remoto no funcionará.
2. **No** publiques `ha.waynehomelab.com` en Cloudflare (solo split DNS en Pi-hole → `10.44.0.1`).

Token API Caddy (zona `waynehomelab.com` únicamente): **Zone:Read** + **DNS:Edit**.

---

## 2) Crear la VM (en el host Proxmox)

Desde el Mac:

```bash
cd /Users/miguel/Proyectos/WayneHomeLab

scp infrastructure/proxmox/create_wireguard_vm.sh pi@192.168.1.100:/tmp/

ssh -t pi@192.168.1.100 \
  'sudo SSH_KEY_FILE=/home/pi/.ssh/authorized_keys bash /tmp/create_wireguard_vm.sh'
```

Anota la MAC:

```bash
ssh -t pi@192.168.1.100 'sudo qm config 102 | grep net0'
```

Espera ~60–90 s:

```bash
ping -c 2 192.168.1.55
ssh pi@192.168.1.55
```

---

## 3) Router

1. Reserva DHCP: MAC **`bc:24:11:e9:6c:c9`** → **`192.168.1.55`**.
2. Port forward **solo** UDP **51820** → `192.168.1.55`.  
   **No** reenvíes 80, 443 ni 8123.
3. **No uses `.54` para el lab:** MAC `7e:9b:d8:fa:86:f8` = MacBook Pro corporativo (`MANDRESG-MAC`). No tocarla.

---

## 4) Instalar WireGuard en la VM

```bash
scp infrastructure/nodes/wireguard/install_wireguard.sh \
    infrastructure/nodes/wireguard/create_peer.sh \
    pi@192.168.1.55:/tmp/

ssh -t pi@192.168.1.55 'sudo bash /tmp/install_wireguard.sh'

ssh -t pi@192.168.1.55 'sudo bash /tmp/create_peer.sh macbook 10'
ssh -t pi@192.168.1.55 'sudo bash /tmp/create_peer.sh iphone 11'
```

Copia los `.conf` fuera (no los commits):

```bash
scp pi@192.168.1.55:/etc/wireguard/peers/macbook.conf ~/Downloads/
scp pi@192.168.1.55:/etc/wireguard/peers/iphone.conf ~/Downloads/
```

Importa en la app WireGuard (Mac / iPhone). DNS del cliente = **Pi-hole** `192.168.1.53`.

---

## 5) Caddy + Cloudflare DNS-01

En la VM:

```bash
scp infrastructure/nodes/wireguard/install_caddy.sh \
    infrastructure/nodes/wireguard/Caddyfile \
    infrastructure/nodes/wireguard/cloudflare.env.example \
    pi@192.168.1.55:/tmp/

ssh -t pi@192.168.1.55 'sudo mkdir -p /etc/caddy && sudo cp /tmp/cloudflare.env.example /etc/caddy/cloudflare.env'
ssh -t pi@192.168.1.55 'sudo nano /etc/caddy/cloudflare.env'   # CF_API_TOKEN=…
ssh -t pi@192.168.1.55 'sudo chmod 600 /etc/caddy/cloudflare.env'

ssh -t pi@192.168.1.55 \
  'sudo CADDYFILE_SRC=/tmp/Caddyfile bash /tmp/install_caddy.sh'
```

Si la download API de Caddy falla (sin SLA), en el **Mac M3 (este repo)**:

```bash
# o: curl → /tmp/caddy-cloudflare-arm64 desde caddyserver.com/api/download … cloudflare
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
GOOS=linux GOARCH=arm64 xcaddy build --with github.com/caddy-dns/cloudflare
scp caddy pi@192.168.1.55:/tmp/caddy-cloudflare
ssh -t pi@192.168.1.55 \
  'sudo CADDY_BINARY=/tmp/caddy-cloudflare CADDYFILE_SRC=/tmp/Caddyfile bash /tmp/install_caddy.sh'
```

Caddy escucha **solo** en `10.44.0.1:443` (`bind`).

---

## 6) Pi-hole — Local DNS

En Pi-hole (UI o CLI), registro local:

```text
10.44.0.1 ha.waynehomelab.com
```

Pi-hole v6 (`dns.hosts` en `/etc/pihole/pihole.toml`). Ejemplo CLI (revisa hosts existentes antes de sobrescribir):

```bash
ssh -t pi@192.168.1.53 \
  "sudo pihole-FTL --config dns.hosts '[\"10.44.0.1 ha.waynehomelab.com\"]'"
```

Si ya hay otros hosts, edita `dns.hosts` en la UI (Expert → All Settings) o mergea el array a mano.

Verifica:

```bash
dig @192.168.1.53 ha.waynehomelab.com +short
# → 10.44.0.1
```

---

## 7) Home Assistant (Network UI)

Desde HA **2026.8**, HTTP se configura en **Ajustes → Sistema → Red** (no ampliar el bloque `http:` en YAML; migrar y quitarlo si aparece repair).

| Ajuste | Valor |
|--------|--------|
| Trust X-Forwarded-For | On |
| Trusted proxies | `192.168.1.55` (solo la VM Caddy; **no** `192.168.1.0/24`) |
| Internal URL | `http://192.168.1.110:8123` |
| External URL | `https://ha.waynehomelab.com` |

Satellite1 / LAN siguen en `http://192.168.1.110:8123`.

---

## 8) Verificar

```bash
bash infrastructure/nodes/wireguard/verify_wireguard.sh
# Con túnel activo (app WireGuard ON):
# SKIP_VPN_HTTPS=0 bash infrastructure/nodes/wireguard/verify_wireguard.sh
```

### Go / no-go

| Prueba | Esperado |
|--------|----------|
| Sin VPN: `https://ha.waynehomelab.com` | No conecta |
| WAN: 80 / 443 / 8123 | No sirven HA |
| Con VPN (datos móviles): `https://ha.waynehomelab.com` | Cert LE válido + UI HA |
| LAN: `http://192.168.1.110:8123` | OK (voz / ESPHome) |
| Host `free -h` | Margen ~1 GB; WG estable a 512 MiB |

### Rollback

1. Quitar DNAT UDP 51820 en el router.
2. `sudo qm stop 102` en el host.
3. External URL de HA → vacía o LAN.
4. Opcional: `sudo qm set 101 --memory 768` si bajaste Pi-hole.

---

## Scripts

| Path | Rol |
|------|-----|
| `infrastructure/proxmox/create_wireguard_vm.sh` | Crea VM 102 |
| `infrastructure/proxmox/wireguard.conf` | Referencia (no aplicar a mano) |
| `infrastructure/nodes/wireguard/install_wireguard.sh` | Server WG en la VM |
| `infrastructure/nodes/wireguard/create_peer.sh` | Peers + QR |
| `infrastructure/nodes/wireguard/install_caddy.sh` | Caddy + Cloudflare |
| `infrastructure/nodes/wireguard/Caddyfile` | Proxy HTTPS |
| `infrastructure/nodes/wireguard/cloudflare.env.example` | Plantilla `CF_API_TOKEN` |
| `infrastructure/nodes/wireguard/verify_wireguard.sh` | Smoke tests |

**Deprecado:** `infrastructure/nodes/core/install_wireguard.sh` y `create_wireguard_peer.sh` (instalaban WG en el host Proxmox). Usa la VM 102.

Tras reboot del host:

```bash
ssh -t pi@192.168.1.100 'sudo qm start 102'   # onboot=1 normalmente
```
