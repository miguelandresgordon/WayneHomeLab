# Satellite1 — actualizar bootloader (flash USB una vez)

El aviso ESPHome `Bootloader too old for OTA rollback` aparece tras un OTA correcto.
El firmware (Mariano, DSP, `api.encryption`) **ya está** en el dispositivo. El
bootloader de fábrica no puede revertir un OTA a medias. Un flash **por el
puerto USB-C del Satellite1** escribe un bootloader nuevo.

Un pendrive solo transporta YAML + secrets. **No** actualiza el bootloader
hasta que conectas el Satellite1 por cable a un PC/Mac y lanzas Install USB.

## Qué no hacer

- No interrumpir el OTA Wi‑Fi si aún corre.
- No generar un `api_encryption_key` nuevo (rompería la API con HA).
- No flashear un `.ota.bin` viejo de Descargas (Mariano-only / sin overlay).
- HAOS en Proxmox **no** ve el USB del Satellite1 (sin passthrough). Flashea
  desde el Mac o el PC Windows con Chrome, no desde la VM.

## Material

1. Cable USB-C del Satellite1 → Mac o PC (datos, no solo carga).
2. Este kit (`satellite1-c7ffe4.yaml` + `secrets.yaml` con Wi‑Fi y
   `api_encryption_key`).
3. Chrome / Edge (Web Serial) **o** ESPHome CLI.

## Opción A — Device Builder (recomendada)

1. Copia este directorio al PC si no estás en el Mac del lab.
2. Confirma que HA → `/config/esphome/` tiene el mismo YAML y `secrets.yaml`.
3. Enchufa el **Satellite1** (no el pendrive) al ordenador.
4. HA → ESPHome Device Builder → Satellite1 → **Install** →
   **Plug into this computer**.
5. Elige el puerto serie (macOS: `cu.usbmodem*` / `cu.wchusbserial*`;
   Windows: `COMx`).
6. Espera COMPILING (si no hay caché) + upload serie. El warning de
   bootloader debe desaparecer en el siguiente arranque.

Si el navegador no lista el puerto: drivers CH34x/CP210x/CDC; en macOS
permite el accesorio; cierra otros `esphome logs` / serial monitors.

## Opción B — ESPHome CLI (mismo YAML)

```bash
# En el directorio del kit (secrets.yaml al lado del YAML)
esphome run satellite1-c7ffe4.yaml --device /dev/cu.usbmodem*
# Windows (PowerShell), sustituye COMx:
# esphome run satellite1-c7ffe4.yaml --device COM3
```

## Empaquetar el kit desde el repo

```bash
USB_VOLUME=/Volumes/MIGUEL ./infrastructure/voice/wake-word/pack_satellite1_usb.sh
```

Destino por defecto: `$USB_VOLUME/wayne-satellite1-usb-flash/`.
`secrets.yaml` se copia desde HAOS Samba o el secrets gitignored local;
nunca se commitea.

## Tras el flash USB

- Satellite1 vuelve a `192.168.1.85` y a HA con la misma encryption key.
- Wake word: Mariano. Probar: «Mariano, enciende la lámpara».
- `input_text.last_stt_text` debe rellenarse.
- Siguientes actualizaciones pueden ser OTA de nuevo (ya con rollback).
