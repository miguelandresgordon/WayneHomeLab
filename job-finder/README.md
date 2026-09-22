# Job Finder

Aplicación doméstica de búsqueda de empleo y autorrelleno asistido (Safari).  
Fases 1–7 locales: auth de dos usuarios, perfil/CV, tokens de extensión, API `analyze`/`fill-result`
y Safari Web Extension con popup de revisión. Sin despliegue en el host Proxmox.

Runbook: [docs/job-finder.md](../docs/job-finder.md)

Spike Safari Web Extension (macOS+iOS): [safari-extension/README.md](safari-extension/README.md)

## Desarrollo local (Mac ARM64)

```bash
cd job-finder
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
bash tests/run_tests.sh
docker compose up --build
```

La portada autenticada permite:

- crear y gestionar tokens de la extensión Safari;
- editar el perfil personal;
- crear y gestionar perfiles de búsqueda y preferencias;
- subir, descargar y seleccionar el CV predeterminado;
- crear y gestionar respuestas reutilizables.

Después de cambiar `.env` o el código, recrear el contenedor:

```bash
docker compose up --build -d --force-recreate
```

```bash
curl -sS http://127.0.0.1:8473/api/v1/health
open http://127.0.0.1:8473/
```

Usuarios de desarrollo (solo `.env` local): `user-a@local.test` / `user-b@local.test`.  
El contenedor limita **256 MiB** de RAM y **0,5 CPU**. Un solo worker uvicorn. Puerto: `127.0.0.1:8473`.
