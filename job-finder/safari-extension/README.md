# Job Finder Safari Web Extension — Spike + inventario genérico

Spike de la fase 4 (validado manualmente en Safari) más el endurecimiento de la fase 5
para inventariar y rellenar formularios. No envía candidaturas, no marca consentimientos
y no lee valores actuales del formulario.

## Estado

- WebExtension Manifest V3 portable en `extension/`
- Proyecto Xcode macOS+iOS generado en `xcode/Job Finder/`
- Inventario de campos visibles sin HTML ni valores, con `schema_version: 1`
- Lista de exclusión: password, hidden, CSRF/token, consentimientos y legales
- Relleno básico de texto y select con eventos `input`, `change` y `blur`
- Adjuntos PDF: solo detección de `File`/`DataTransfer`; prueba real pendiente
- **Fase 5:** radios agrupados por `name`, leyenda de `fieldset` como fallback de etiqueta,
  `select multiple` marcado para revisión manual, shadow DOM abierto e iframes del mismo
  origen recorridos recursivamente (los de otro origen se cuentan en `blocked_frames`)

## Pruebas automáticas

```bash
cd job-finder/safari-extension
npm test
node --check extension/popup.js
node --check extension/content.js
node --check extension/form-tools.js
```

Compilar sin firma:

```bash
xcodebuild \
  -project "xcode/Job Finder/Job Finder.xcodeproj" \
  -scheme "Job Finder (macOS)" \
  -destination "platform=macOS,arch=arm64" \
  -derivedDataPath /tmp/job-finder-derived-macos \
  CODE_SIGNING_ALLOWED=NO build

xcodebuild \
  -project "xcode/Job Finder/Job Finder.xcodeproj" \
  -scheme "Job Finder (iOS)" \
  -destination "generic/platform=iOS Simulator" \
  -derivedDataPath /tmp/job-finder-derived-ios \
  CODE_SIGNING_ALLOWED=NO build
```

## Prueba manual en Safari macOS

1. Abrir `xcode/Job Finder/Job Finder.xcodeproj`.
2. Seleccionar el esquema **Job Finder (macOS)** y el Mac local.
3. En *Signing & Capabilities*, elegir el equipo personal si Xcode lo solicita.
4. Ejecutar la app con **Run**.
5. En Safari → Ajustes → Extensiones, activar **Job Finder**.
6. Servir el formulario sintético:

   ```bash
   cd job-finder/safari-extension
   python3 -m http.server 8765 --directory tests/fixtures
   ```

7. Abrir `http://127.0.0.1:8765/application-form.html`.
8. Pulsar el icono Job Finder y después **Analizar formulario**.

Resultado esperado:

- detecta nombre, correo, teléfono, modalidad, motivación, CV y consentimiento;
- no lista password, hidden, CSRF ni botón de envío;
- CV y consentimiento aparecen como revisión manual;
- el popup indica si Safari expone `File` y `DataTransfer`;
- no modifica ni envía el formulario.

### Fixture avanzada (fase 5)

Con el mismo servidor (`python3 -m http.server 8765 --directory tests/fixtures`), abrir
`http://127.0.0.1:8765/advanced-form.html` y repetir **Analizar formulario**. Resultado esperado:

- **Modalidad preferida** aparece como un único elemento de revisión manual (grupo de radios),
  no tres filas repetidas;
- **Tecnologías** (`select multiple`) aparece como revisión manual;
- **Código de referencia** (campo `disabled`) no aparece en la lista;
- **Referencia interna**, dentro del iframe embebido del mismo origen, sí aparece;
- **Disponibilidad (fecha)**, dentro del componente `<job-finder-availability>` con shadow DOM
  abierto, sí aparece;
- si el navegador bloquea el iframe por algún motivo, el aviso inferior indica cuántos
  `iframe`(s) no se pudieron inspeccionar (`blocked_frames`).

## Gate de adjuntos PDF

La presencia de `File` y `DataTransfer` no demuestra que Safari permita asignar un PDF
descargado por la extensión a `input.files`. Esa prueba requiere gesto del usuario, un PDF
de prueba y verificación visual del nombre aceptado por la página. Si falla, el producto
usará descarga + resaltado del campo para adjuntar manualmente.

## Regenerar el proyecto

Apple renombró el conversor a `safari-web-extension-packager`:

```bash
xcrun safari-web-extension-packager ./extension \
  --project-location ./xcode \
  --app-name "Job Finder" \
  --bundle-identifier com.waynehomelab.jobfinder \
  --swift --copy-resources --no-open --no-prompt --force
```

Regenerar después de cambiar archivos en `extension/`, porque el proyecto contiene una copia
de esos recursos.
