# Job Finder

Asistente doméstico de empleo (dos usuarios). Este runbook cubre hasta el **kit de la fase 8** (auth, perfil/CV, inventario Safari, API `analyze`/`fill-result`, sesiones multipágina y ensayo LinkedIn → ATS). El **go/no-go** de F8 es manual: no hay despliegue en `waynelab-core`.

**Repo:** se queda en WayneHomeLab hasta el go/no-go de F8 en un ATS real, o hasta F14 (GHCR + host). Extraer ahora no desacopla Caddy/Pi-hole/HA.

## Alcance actual

- FastAPI + Jinja2 (login real, dos usuarios)
- Contraseñas Argon2id; cookies `jf_session` (HttpOnly) y `jf_csrf`
- CSRF en formularios HTML y cabecera `X-CSRF-Token` en la API (multipart: campo `csrf_token`)
- Tokens de extensión (`Authorization: Bearer`); CSRF no aplica al Bearer. Un Bearer inválido no cae a la cookie.
- SQLite con WAL + Alembic
- Health: `GET /api/v1/health`
- Docker Compose local, límites 256 MiB / 0,5 CPU, usuario no root, filesystem de solo lectura
- **Fase 3** — perfil, perfiles de búsqueda y CV, todo aislado por usuario (`user_id` en cada fila, tests IDOR):
  - `GET/PUT /api/v1/profile` — identidad y contacto (PII mínima: nombre, teléfono, ubicación, enlaces, resumen)
  - `GET/POST/PUT/DELETE /api/v1/search-profiles` — perfiles de búsqueda con nombre único por usuario y un único `is_default`
  - `PUT /api/v1/search-profiles/{id}/preferences` — puestos, ubicaciones, modalidad, salario, disponibilidad, sponsorship, reubicación, viaje
  - `POST /api/v1/resumes` (multipart, solo PDF, máx. 5 MiB por defecto) / `GET /api/v1/resumes` / `DELETE /api/v1/resumes/{id}` / `POST /api/v1/resumes/{id}/default` / `GET /api/v1/resumes/{id}/file` (descarga con `Cache-Control: no-store`)
  - `GET/POST/PUT/DELETE /api/v1/reusable-answers` — respuestas guardadas explícitamente por el usuario (nunca autogeneradas)
  - CV almacenados en `JOB_FINDER_RESUMES_DIR` (`/data/resumes` en el contenedor) con nombre opaco (`uuid4().pdf`); solo se valida la cabecera `%PDF-` y el tamaño, nunca se confía en el `Content-Type` del cliente
- **Fases 6–7** — autorrelleno asistido:
  - `GET/POST/DELETE /api/v1/auth/extension-tokens` — solo sesión web; el valor crudo se muestra una vez
  - `POST /api/v1/form-sessions` — reutiliza `(user, origin, tab_key)` mientras la sesión está abierta; un origen distinto crea otra sesión
  - `POST /api/v1/form-sessions/{id}/analyze` — inventario `schema_version: 1` → correspondencias deterministas (never-fill gana en el servidor)
  - `POST /api/v1/form-sessions/{id}/fill-result` — qué se aplicó / falló (sin valores de password)
  - `POST /api/v1/form-sessions/{id}/complete` — marca la candidatura en Job Finder, **no** envía el formulario del ATS
  - Campos ya rellenados (`fill_status=applied`) salen como `skip` en la siguiente página de la misma sesión

## Interfaz web

Tras iniciar sesión, `/` ofrece una interfaz Jinja2 + JavaScript ligero:

- tokens de la extensión Safari (crear / revocar);
- editar el perfil personal;
- crear, editar, eliminar y marcar como predeterminados los perfiles de búsqueda;
- configurar puestos, ubicaciones, modalidad, jornada, nivel y salario mínimo;
- subir, descargar, eliminar y seleccionar el CV predeterminado;
- crear, editar y eliminar respuestas reutilizables.

La interfaz consume la API `/api/v1`, envía el token CSRF en cada mutación y no interpreta los datos del usuario como HTML.

## Safari Web Extension (fases 4–8)

El código portable está en `job-finder/safari-extension/`:

- Manifest V3 con `activeTab` y `optional_host_permissions`; el popup pide el origen de la pestaña **antes** de inyectar scripts (necesario en ATS `https://`);
- popup: token Bearer, analizar, revisar correspondencias, rellenar solo aprobados, descargar el CV predeterminado, marcar candidatura;
- tras analizar, resalta campos `review` / file (nunca legales ni password) y hace scroll al primero;
- exclusión de passwords, hidden, CSRF/tokens, botones y consentimientos;
- los descriptores no contienen HTML ni valores actuales del ATS;
- relleno de texto/select con eventos DOM; radios, legales y `input[type=file]` no se rellenan solos;
- MutationObserver con debounce: si el DOM SPA cambia, el siguiente análisis regenera los handles;
- proyecto Xcode generado para macOS e iOS;
- fixtures sintéticas (`application-form.html`, `advanced-form.html`, `bizneo-like-form.html`) y tests Node.

La asignación automática de PDF a `input[type=file]` sigue siendo un **gate manual**: usa **Descargar CV predeterminado** en el popup y adjúntalo a mano.
El procedimiento y el fallback están en `job-finder/safari-extension/README.md`.

## Inventario genérico (fase 5)

En `job-finder/safari-extension/extension/form-tools.js`:

- radios que comparten `name` → un descriptor `radio-group`;
- etiqueta: `<legend>` del `<fieldset>` como último recurso;
- `select multiple` → revisión manual;
- shadow roots abiertos e iframes del mismo origen; cross-origin en `blocked_frames`;
- `schema_version: 1`. La sección y, si hay varias entradas, su índice viajan en `signals` (`section`, `entry`). Un campo que ya tiene contenido se marca `already_filled`; el texto del ATS no se envía.

## Fase 8 — go/no-go (manual)

La API y la extensión cubren el vertical slice sintético (tests `test_form_sessions.py` / `test_mapping.py`). La prueba real no se automatiza: hace falta Safari, una oferta LinkedIn y el ATS con tu sesión. Plantilla de log: [job-finder/docs/f8-trial-log.example.md](../job-finder/docs/f8-trial-log.example.md) → copia a `job-finder/docs/f8-trial-log.md` (gitignored).

**Oferta válida:** LinkedIn → **Apply en la web de la empresa** (portal externo: Bizneo u otro). **No** Easy Apply in-app. **No** pulses Enviar ni marques legales.

### Pre-vuelo

1. `docker compose up --build` en `job-finder/` y `curl http://127.0.0.1:8473/api/v1/health`.
2. En la UI, rellena perfil (nombre completo, que se parte en nombre/apellidos) + CV PDF + un perfil de búsqueda. Crea un token de extensión y pégalo en el popup.
3. Sideload Xcode: esquema **Job Finder (macOS)**. Activa la extensión en Safari. Al analizar un ATS `https://`, acepta el permiso del origen si Safari lo pide.
4. Ensayo local: `python3 -m http.server 8765 --directory tests/fixtures` (desde `job-finder/safari-extension/`) y abre `bizneo-like-form.html`. Analizar → revisar → rellenar aprobados. Consentimientos y Enviar intactos. Nombre/Apellidos deben rellenarse. En el paso 2, volver a analizar: los campos ya aplicados salen como omitidos.

### Ensayo real

5. Oferta real con portal externo. Analizar, revisar, rellenar aprobados. Los campos pendientes (`review` / file) se resaltan en la página. Descarga el CV desde el popup y adjúntalo a mano si el `input[type=file]` no acepta el archivo.
6. **Marcar candidatura** en el popup (estado `applied` en Job Finder). El formulario del ATS **no** se envía.
7. Rellena el log anonimizado: hostname del ATS, conteos fill/review/never/skip, PDF ok/fallback, veredicto.

### Criterios de aceptación (autorrelleno; sin HA/CI/Gmail)

- Inventario sin HTML ni valores actuales del ATS; el backend no recibe cookies.
- Correspondencias explicables; fill **solo** de campos aprobados.
- Never-fill: password, hidden, CSRF, consentimientos y legales.
- Submit / Enviar intacto; no se automatiza Easy Apply ni se raspa LinkedIn.
- Origen nuevo = sesión nueva; campos ya aplicados = `skip` en la misma sesión.
- `blocked_frames` si hay iframe cruzado; la extensión no adivina el DOM inaccesible.
- Identidad / contacto / modalidad rellenados y verificables en el DOM (fill útil o, como mínimo, fill parcial documentado).
- Application `applied` **sin** enviar el ATS.
- PII de terceros y HTML real **no** se commitean.

### Veredicto

- **fill útil** — identidad/contacto/modalidad rellenados y comprobados; legales y envío intactos.
- **fill parcial** — parte útil + campos a mano (file, radios, custom elements); sigue siendo go condicionado.
- **no-go** — DOM inaccesible, iframe cross-origin que contiene el formulario, permiso denegado, o never-fill/submit rotos.

El checkbox de F8 en `AGENTS.md` se marca **después** de anotar este veredicto, no al dejar el kit listo.

## Desarrollo en el Mac

```bash
cd job-finder
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
bash tests/run_tests.sh
cd safari-extension && npm test
docker compose up --build
```

Comprobar:

```bash
curl -sS http://127.0.0.1:8473/api/v1/health
open http://127.0.0.1:8473/
```

Usuarios locales por defecto (cámbialos en `.env`): `user-a@local.test` y `user-b@local.test`.

## Fuera de alcance (aún)

- Instalar Docker en el host Proxmox
- Cambiar Caddy o Pi-hole
- Gmail, scoring, ingestión de ofertas, digest HA, HTTPS `jobs.waynehomelab.com`

El HTTPS VPN se añade en F14, con `verify_wireguard.sh` / `verify_pihole.sh` en verde.
