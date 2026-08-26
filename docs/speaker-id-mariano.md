# Speaker ID Mariano — Runbook

Guía operativa para enrolar perfiles de voz (tipo Alexa) e identificar quién habla en cada comando del Satellite1.

## Arquitectura

```
Satellite1 → HA Assist Pipeline
  → debug WAV en /share/assist_pipeline/<run_id>/
  → folder_watcher (created) → automatización speaker_id_on_command
  → add-on speaker-id-mariano (POST /identify)
  → input_text.current_speaker + evento speaker_identified
```

El enrolamiento combina **grabación local en el Mac** (micro nativo) + **cómputo en Colab** (almacenamiento/CPU remotos). La inferencia corre en un **add-on dentro de la HAOS VM**.

> **Nota sobre disco y micrófono.** El speaker ID es ligero (~32 MB: modelo 26 MB + clips diminutos), nada que ver con el wake word (~25 GB). 7 GB de Drive sobran. El micro se graba **en el Mac**, no en Colab: el kernel de Colab es remoto y no accede al micro, y la grabación por navegador no funciona desde Cursor. **No se necesita MCP ni Chromium.**

## 1. Grabar muestras en el Mac

```bash
# Dependencias (una vez)
brew install portaudio
pip3 install sounddevice soundfile numpy

# Grabar por persona
python3 infrastructure/voice/speaker-id/record_samples.py --speaker miguel --count 10
python3 infrastructure/voice/speaker-id/record_samples.py --speaker ana --count 10
```

Genera `infrastructure/voice/speaker-id/samples/<persona>/clip_NN.wav` (pocos MB en total).

> Alternativa con `ffmpeg`:
> ```bash
> ffmpeg -f avfoundation -i ":0" -ar 16000 -ac 1 -t 4 samples/miguel/clip_01.wav
> ```

## 2. Subir muestras a Google Drive

Copia `samples/` a `MyDrive/wayne-speaker-id/samples/` (drag&drop en drive.google.com o Google Drive para escritorio).

## 3. Enrolar en Colab

1. Abre [`infrastructure/voice/speaker-id/notebooks/train_speaker_profiles.ipynb`](../infrastructure/voice/speaker-id/notebooks/train_speaker_profiles.ipynb) con kernel **Google Colab**.
2. Ejecuta celdas 1–2 (setup + descarga modelo).
3. Edita `SPEAKERS` (celda 3) con tus nombres.
4. Celda 5a: monta Drive e importa las muestras.
5. Ejecuta celdas 6–9 (centroides, umbral, evaluación, export).
6. Descarga `speaker-id-mariano-export.zip`.

> Si prefieres clips del Satellite1, súbelos como ZIP en la celda 5b (solo en la UI web de Colab).

### Validar (opcional, en Mac)

```bash
python3 infrastructure/voice/speaker-id/validate_profiles.py \
  ~/Downloads/speaker_profiles.json
```

## 4. Copiar artefactos a HAOS

Via Samba (`\\192.168.1.110\share` o montaje `/share`):

```
/share/speaker-id/
├── wespeaker_en_voxceleb_resnet34.onnx
├── speaker_profiles.json
└── config.json
```

Crea la carpeta si no existe.

## 5. Instalar add-on en HAOS

```bash
# Desde Mac — copiar add-on al supervisor
scp -r home-assistant/addons/speaker-id-mariano/ \
  root@192.168.1.110:/addons/speaker_id_mariano/
```

En HA:
1. **Ajustes → Sistema → Reiniciar supervisor**
2. **Ajustes → Complementos → Complemento local → Speaker ID Mariano → Instalar → Iniciar**
3. Verificar: `http://192.168.1.110:10400/health`

## 6. Desplegar config de Home Assistant

```bash
HA_HOST=192.168.1.110 ./infrastructure/voice/wake-word/deploy_ha_voice_config.sh
```

O copia manualmente `home-assistant/` a `/config/` en HAOS.

Componentes clave ya en el repo:
- `assist_pipeline.debug_recording_dir: /share/assist_pipeline` (activo)
- `allowlist_external_dirs` para `/share/assist_pipeline` y `/share/speaker-id`
- Folder Watcher (configurar via UI, ver sección anterior)
- `input_text.current_speaker`
- Automatizaciones `speaker_id_on_command` y `speaker_id_purge_wavs`

### Folder Watcher (si no arranca por YAML)

Configura via UI:
1. **Ajustes → Dispositivos → Añadir integración → Folder Watcher**
2. Carpeta: `/share/assist_pipeline`
3. Patrones: `*.wav`
4. Eventos: `created`

## 7. Verificar end-to-end

1. Di un comando al Satellite1: «Enciende la lámpara».
2. Comprueba que aparece un WAV en `/share/assist_pipeline/`.
3. Comprueba `input_text.current_speaker` en **Herramientas de desarrollo → Estados**.
4. Revisa el evento `speaker_identified` en **Herramientas de desarrollo → Eventos**.

## 8. Usar identidad en automatizaciones

Ejemplo — notificación solo al hablante identificado:

```yaml
trigger:
  - platform: event
    event_type: speaker_identified
condition:
  - condition: template
    value_template: "{{ trigger.event.data.person == 'miguel' }}"
action:
  - service: notify.mobile_app
    data:
      title: "Te escuché, Miguel"
      message: "Comando procesado."
```

Ejemplo — presencia por voz:

```yaml
trigger:
  - platform: event
    event_type: speaker_identified
condition:
  - condition: template
    value_template: "{{ trigger.event.data.is_known }}"
action:
  - service: input_boolean.turn_on
    target:
      entity_id: "input_boolean.presencia_{{ trigger.event.data.person }}"
```

## 9. Re-enrolar / añadir persona

1. Edita `SPEAKERS` en el notebook Colab.
2. Añade muestras y re-exporta.
3. Copia nuevo `speaker_profiles.json` a `/share/speaker-id/`.
4. Recarga perfiles:
   ```bash
   curl -X POST http://192.168.1.110:10400/reload
   ```
   O reinicia el add-on.

## Calibración

| Síntoma | Ajuste |
|---------|--------|
| Siempre `desconocido` | Bajar `threshold` en add-on (0.6 → 0.5) o re-enrolar con más clips |
| Confunde dos personas | Subir `margin` (0.05 → 0.10) o añadir clips diferenciadores |
| Falsos positivos | Subir `threshold` (0.6 → 0.65) |

Ajusta en **Ajustes → Complementos → Speaker ID Mariano → Configuración**.

## Troubleshooting

| Problema | Causa / solución |
|----------|------------------|
| No aparecen WAV | `debug_recording_dir` desactivado — revisar `configuration.yaml` |
| Automatización no dispara | Folder Watcher no configurado o patrón incorrecto |
| Add-on no arranca | Falta modelo ONNX o `speaker_profiles.json` en `/share/speaker-id/` |
| Embeddings incompatibles | Modelo ONNX distinto entre Colab y add-on — usar mismo archivo |
| Disco lleno | Automatización `speaker_id_purge_wavs` cada 30 min; desactivar debug tras pruebas |

## Referencias

- [sherpa-onnx speaker models](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models)
- [HA Assist troubleshooting](https://www.home-assistant.io/voice_control/troubleshooting/)
- [Wake word Mariano](wake-word-mariano.md)
