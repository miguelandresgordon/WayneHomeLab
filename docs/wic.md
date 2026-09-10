# Weather Intelligence Center — runbook local

v1 slim: Vite + React + Tailwind + Hono, un contenedor Docker en el Mac. **No desplegar** a la RPi 3B, Proxmox, Caddy ni Pi-hole hasta que se pida explícitamente.

## Qué es

Observatorio doméstico: cielo AEMET + tres controles de salón (lámpara Xiaomi, `tv_ga_2`, radio). Independiente de Lovelace. No añade automatizaciones HA.

## Requisitos

- Docker Desktop en marcha (Mac ARM64)
- Rama `feature/wic-v1-slim`

## Arranque

```bash
cd weather-intelligence
cp .env.example .env
docker compose up --build
```

| URL | Uso |
|-----|-----|
| http://localhost:5173 | UI |
| http://localhost:3000/api/health | API |
| http://localhost:3000/api/home | ViewModel Home |
| http://localhost:3000/api/context | JSON de contexto (nadie ejecuta acciones solo) |

Parar: `Ctrl+C` o `docker compose down`.

Si cambias dependencias: `docker compose build --no-cache && docker compose up`. Si `node_modules` del volumen se queda viejo: `docker compose down -v`.

## Datos

| Variable | Local |
|----------|--------|
| `WIC_DEMO=1` | Fixtures, sin AEMET (por defecto) |
| `AEMET_API_KEY` | OpenData; `WIC_MUNICIPIO_INE` + `WIC_IDEMA` de tu estación |
| `HA_TOKEN` | Long-lived token HA; allowlist lámpara / tele / radio |
| SQLite | `weather-intelligence/data/wic.db` |

Import de históricos:

```bash
docker compose exec wic npm run import -- fixtures/aemet-clima-sample.csv
```

CSV genérico: `timestamp,temp_c,humidity,wind_ms,precip_mm,sky_text`  
CSV AEMET climatología diaria: `fecha,indicativo,tmed,prec,velmedia` (viento km/h → m/s).

## Tests

```bash
docker compose exec wic npm test
```

## Allowlist HA

- `light.yeelink_mono6_6409_light`
- `media_player.tv_ga_2` vía `script.encender_tele` / `script.apagar_tele`
- `script.poner_radio` / `script.parar_radio`

No mute Satellite1. No Bravia on/off. No Antela. No tocar `automations.yaml`.

## Fuera de v1

Radar, satélite, PWA, WebSocket HA, Energy, agente que pulse él solo, DietPi, Caddy `weather.waynehomelab.com`.
