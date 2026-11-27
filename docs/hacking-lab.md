# Laboratorio de hacking (privado, aislado)

Entorno de **práctica** en Docker (`hacking-lab/`): un Kali con herramientas del
repositorio oficial, objetivos **deliberadamente vulnerables** en una red sin
salida, y toda la navegación de Kali saliendo por **Mullvad** (WireGuard, vía
gluetun). Opcional: Tor encima de Mullvad.

## Reglas

1. **Solo objetivos propios**: los contenedores de este laboratorio (Juice Shop,
   DVWA, WebGoat) o plataformas que lo autorizan expresamente (p. ej. Hack The
   Box, TryHackMe, en sus VPN). Nunca equipos de la LAN de casa (ni el MacBook
   corporativo `.54`), del trabajo o de terceros.
2. Practicar es **legal** solo con permiso del dueño del sistema. La VPN da
   privacidad, no permiso.
3. Antes de cada sesión: `./lab.sh verify` (IP de Mullvad, sin **fuga de DNS**).
   Si algo falla, no se usa.
4. Nada de herramientas a medida ni malware: solo paquetes de Kali.
5. La clave de Mullvad vive en `hacking-lab/.env` (gitignored). Nunca al repo.

## Diseño

| Pieza | Red | Salida |
|---|---|---|
| gluetun (Mullvad WireGuard, `wg0`) | `default` + `lab_internal` (`.2`) | túnel Mullvad |
| kali, tor | `network_mode: service:gluetun` | solo por el túnel |
| juice-shop `.10`, dvwa `.11`, dvwa-db `.12`, webgoat `.13` | `lab_internal` (`internal: true`) | ninguna |

- **Kill switch**: el firewall de gluetun solo deja salir por `wg0` y hacia
  `172.31.77.0/24`. Si el túnel cae, Kali se queda sin red (no sale por casa).
- **DNS**: resolvedor de Mullvad `10.64.0.1` por el túnel (sin DoT, sin Pi-hole,
  sin router). Los nombres de los objetivos van a `/etc/hosts` de Kali.
- Ningún puerto publicado en la LAN. Imágenes fijadas por versión o digest;
  límites de memoria/CPU en todos los servicios.

## Uso

```bash
cd hacking-lab
cp .env.example .env          # WIREGUARD_PRIVATE_KEY y WIREGUARD_ADDRESSES de
                              # https://mullvad.net/account/wireguard-config
./lab.sh up                   # gluetun + kali + juice-shop + dvwa
./lab.sh verify               # IP / DNS / aislamiento
./verify_lab.sh --kill        # + prueba del kill switch (reinicia el túnel)
./lab.sh shell                # dentro: curl http://juice-shop:3000, nmap dvwa…
./lab.sh up-full              # + WebGoat (~600 MB)
./lab.sh tor                  # Tor: proxychains4 curl https://check.torproject.org
./lab.sh down
```

DVWA: `http://dvwa` → `admin` / `password` → *Setup* → *Create database*.
`workspace/` (montado en `/root/workspace`) es para tus notas; no se versiona.

## Raspberry Pi 3 (1 GB)

`cp .env.rpi3.example .env` (límites bajos) y solo el perfil ligero, sin
WebGoat. Todas las imágenes tienen variante `arm64`. En el Mac, Docker Desktop
guarda sus datos en el disco externo (`/Volumes/EXTERNALSTG/DockerDesktop`).
