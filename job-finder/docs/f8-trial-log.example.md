# Job Finder F8 — log de ensayo (plantilla)

Copia este archivo a `f8-trial-log.md` (gitignored). No pegues HTML del ATS, cookies, passwords ni valores rellenados. Solo hostname, conteos y señales (`name` / `id` / `label`).

## Contexto

- Fecha:
- Job Finder local: `http://127.0.0.1:8473` health 200: sí / no
- Extensión sideload (esquema Job Finder macOS): sí / no
- Ensayo sintético `bizneo-like-form.html` (paso 1 → Continuar → re-analizar = skip): sí / no
- Oferta: LinkedIn **Apply en web de empresa** (no Easy Apply): sí / no
- ATS hostname (sin path ni query):
- ¿Iframe de otro origen / `blocked_frames`?:

## Conteos (después de Analizar)

- fill:
- review (incl. file / radios):
- never (legales, password, CSRF, hidden):
- skip (ya resueltos en la sesión):
- `blocked_frames`:

## Fill

- Campos de identidad/contacto/modalidad rellenados y verificables en el DOM: sí / parcial / no
- Legales, password y botón Enviar intactos: sí / no
- CV: adjunto a mano / el portal aceptó el archivo / no había campo file
- Marcar candidatura en el popup (el ATS **no** se envió): sí / no

## Señales sin mapear (anonimizadas)

| name | id | label (sin valor) | notas |
|------|----|-------------------|-------|
|      |    |                   |       |

## Veredicto

- [ ] fill útil
- [ ] fill parcial
- [ ] no-go

Motivo (DOM inaccesible, iframe cross-origin, custom elements opacos, permiso denegado, etc.):
