# Weather Intelligence Center (v1 slim)

App meteorológica + salón, independiente de Lovelace. **Solo local con Docker Desktop.** No hay despliegue a RPi 3B, Caddy ni Pi-hole en esta rama.

## Arranque

```bash
cd weather-intelligence
cp .env.example .env
docker compose up --build
```

- UI: http://localhost:5173
- API: http://localhost:3000/api/health

`WIC_DEMO=1` (por defecto en `.env.example`) sirve fixtures. No hace falta clave AEMET ni token de HA para ver la UI.

Para hablar con HA en LAN, rellena `HA_TOKEN` en `.env` y deja `HA_BASE_URL=http://192.168.1.110:8123`. Docker Desktop en Mac llega a esa IP.

## Tests

```bash
docker compose exec wic npm test
```

Import de históricos AEMET (CSV/JSON) al SQLite local:

```bash
docker compose exec wic npm run import -- fixtures/aemet-clima-sample.csv
```

## Qué incluye v1

- Home: frase de cielo, temperatura, 12 h, insight, alféizar (lámpara / tele / casa)
- Casa: lámpara, tele, radio (allowlist HA)
- AEMET OpenData cuando hay `AEMET_API_KEY`
- SQLite en `data/wic.db`
- `GET /api/context` JSON (sin agente que ejecute solo)

Sin radar, satélite, PWA, Grafana, Influx, Postgres, Redis, Next.js ni despliegue remoto.

Runbook: [docs/wic.md](../docs/wic.md)
