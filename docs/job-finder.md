# Job Finder

Asistente doméstico de empleo (dos usuarios). Este runbook cubre hasta la **fase 3** (esqueleto + autenticación + perfiles/CV/respuestas reutilizables). No hay despliegue en `waynelab-core` todavía.

## Alcance actual

- FastAPI + Jinja2 (login real, dos usuarios)
- Contraseñas Argon2id; cookies `jf_session` (HttpOnly) y `jf_csrf`
- CSRF en formularios HTML y cabecera `X-CSRF-Token` en la API (multipart: campo `csrf_token`)
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

## Interfaz web

Tras iniciar sesión, `/` ofrece una interfaz Jinja2 + JavaScript ligero para las funciones de la fase 3:

- editar el perfil personal;
- crear, editar, eliminar y marcar como predeterminados los perfiles de búsqueda;
- configurar puestos, ubicaciones, modalidad, jornada, nivel y salario mínimo;
- subir, descargar, eliminar y seleccionar el CV predeterminado;
- crear, editar y eliminar respuestas reutilizables.

La interfaz consume la API `/api/v1`, envía el token CSRF en cada mutación y no interpreta los datos del usuario como HTML.

## Safari Web Extension (fase 4, spike)

El spike portable está en `job-finder/safari-extension/`:

- Manifest V3 con `activeTab`, sin acceso permanente a todas las webs;
- popup para inventariar campos visibles de la pestaña activa;
- exclusión de passwords, hidden, CSRF/tokens, botones y consentimientos;
- los descriptores no contienen HTML ni valores actuales;
- relleno básico de texto/select con eventos DOM;
- proyecto Xcode generado para macOS e iOS;
- fixture sintética y tests Node sin dependencias;
- **validado manualmente en Safari** (popup, permisos de sitio, DOM y el aviso de capacidades `File`/`DataTransfer`).

La asignación automática de PDF a `input[type=file]` sigue siendo un **gate manual**:
detectar `File`/`DataTransfer` no garantiza que el portal acepte el archivo. El procedimiento
y el fallback están documentados en `job-finder/safari-extension/README.md`.

## Inventario genérico (fase 5)

Endurecido sobre el spike de la fase 4, en `job-finder/safari-extension/extension/form-tools.js`:

- los radios que comparten `name` se agrupan en un único descriptor `radio-group` con
  `options` (evita listar el mismo grupo N veces en la revisión);
- la etiqueta usa como último recurso la `<legend>` del `<fieldset>` que envuelve el campo
  (útil para radios y para campos sin `<label>` explícito);
- `select multiple` se marca `multiple: true` y pasa a revisión manual (`multi_select_review`):
  el relleno de una lista de valores llega en la fase 6, no antes;
- se recorren los **shadow roots abiertos** (`element.shadowRoot`) de forma recursiva, para
  cubrir componentes personalizados de los ATS;
- se recorren los **iframes del mismo origen** (`iframe.contentDocument`); los de otro origen
  no se pueden inspeccionar y se cuentan en `blocked_frames` (nunca se adivina su contenido);
- el inventario devuelve `schema_version: 1` para que el backend (fase 6) pueda validar el
  contrato sin romperse ante cambios futuros.

Fixture ampliada para la prueba manual: `tests/fixtures/advanced-form.html` (+ `embedded-frame.html`
para el caso de iframe del mismo origen) cubre radios agrupados, `select multiple`, fieldset/legend,
un campo deshabilitado, un iframe y un componente con shadow DOM abierto. La fixture original
(`application-form.html`) se mantiene para la prueba básica de la fase 4.

## Desarrollo en el Mac

```bash
cd job-finder
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
bash tests/run_tests.sh
docker compose up --build
```

Para aplicar cambios en `.env` o reconstruir los assets:

```bash
docker compose up --build -d --force-recreate
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
- Gmail, integración backend de la extensión, autorrelleno completo, formularios multipágina, scoring y seguimiento

El HTTPS `jobs.waynehomelab.com` (VPN, mismo patrón que HA) se añade en la fase de despliegue, con `verify_wireguard.sh` / `verify_pihole.sh` en verde.
