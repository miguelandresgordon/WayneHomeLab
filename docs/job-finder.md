# Job Finder

Asistente doméstico de empleo (dos usuarios). Este runbook cubre hasta la **fase 7** (auth, perfil/CV, inventario Safari, API `analyze`/`fill-result` y sesiones multipágina). La **fase 8** (prueba real LinkedIn → ATS) es un gate manual. No hay despliegue en `waynelab-core`.

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

## Safari Web Extension (fases 4–7)

El código portable está en `job-finder/safari-extension/`:

- Manifest V3 con `activeTab`, sin acceso permanente a todas las webs;
- popup: token Bearer, analizar, revisar correspondencias, rellenar solo aprobados, marcar candidatura;
- exclusión de passwords, hidden, CSRF/tokens, botones y consentimientos;
- los descriptores no contienen HTML ni valores actuales del ATS;
- relleno de texto/select con eventos DOM; radios, legales y `input[type=file]` no se rellenan solos;
- MutationObserver con debounce: si el DOM SPA cambia, el siguiente análisis regenera los handles;
- proyecto Xcode generado para macOS e iOS;
- fixtures sintéticas (`application-form.html`, `advanced-form.html`, `bizneo-like-form.html`) y tests Node.

La asignación automática de PDF a `input[type=file]` sigue siendo un **gate manual**.
El procedimiento y el fallback están en `job-finder/safari-extension/README.md`.

## Inventario genérico (fase 5)

En `job-finder/safari-extension/extension/form-tools.js`:

- radios que comparten `name` → un descriptor `radio-group`;
- etiqueta: `<legend>` del `<fieldset>` como último recurso;
- `select multiple` → revisión manual;
- shadow roots abiertos e iframes del mismo origen; cross-origin en `blocked_frames`;
- `schema_version: 1`.

## Fase 8 — go/no-go (manual)

La API y la extensión ya cubren el vertical slice sintético (tests `test_form_sessions.py`). La prueba real no se puede automatizar aquí: hace falta Safari, una oferta LinkedIn y el ATS (Bizneo u otro) con tu sesión.

Checklist:

1. `docker compose up --build` en `job-finder/` y `curl http://127.0.0.1:8473/api/v1/health`.
2. En la UI, rellena perfil + CV PDF + un perfil de búsqueda. Crea un token de extensión y pégalo en el popup.
3. Sideload Xcode: esquema **Job Finder (macOS)**. Activa la extensión en Safari.
4. Ensayo local: `python3 -m http.server 8765 --directory tests/fixtures` y abre `bizneo-like-form.html`. Analizar → revisar → rellenar aprobados. Consentimientos y Enviar intactos. En el paso 2, volver a analizar: los campos ya aplicados salen como omitidos.
5. Oferta real: LinkedIn → Apply → portal externo. **No pulses Enviar ni marques legales.** Analizar, revisar, rellenar. Adjunta el CV a mano si el `input[type=file]` no acepta el archivo.
6. Marcar candidatura en el popup. Anota go/no-go: fill útil / fill parcial / no-go (DOM inaccesible, iframe cross-origin, etc.).

Criterio de éxito: campos de identidad/contacto/modalidad rellenados y verificables; legales, password y envío sin tocar; HTML/cookies del ATS nunca salen al backend.

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
