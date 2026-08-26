# Speaker ID Mariano — Enrolamiento e inferencia

Identificación de hablante (perfiles de voz tipo Alexa) para el asistente Mariano.

## Componentes

| Componente | Ubicación | Función |
|------------|-----------|---------|
| Notebook Colab | `notebooks/train_speaker_profiles.ipynb` | Enrolar voces sin disco local |
| Validador | `validate_profiles.py` | Validar `speaker_profiles.json` |
| Add-on HAOS | `home-assistant/addons/speaker-id-mariano/` | Inferencia en la VM |
| Runbook | `docs/speaker-id-mariano.md` | Guía operativa completa |

## Por qué este flujo (almacenamiento y micrófono)

El enrolamiento de voz es **muy ligero** (~32 MB total): modelo ONNX ~26 MB + clips diminutos (~128 KB cada uno). Nada que ver con el wake word Mariano (~25 GB de datasets). **Con 7 GB libres en Drive sobra de sobra.**

El micrófono se graba **en local en el Mac**, no en Colab, porque:
- El kernel de Colab corre en remoto: no tiene acceso a tu micro.
- La grabación por navegador (JS/MediaRecorder) solo funciona en la UI web de Colab, **no desde Cursor**.
- Grabar local da WAV 16 kHz mono limpio, sin transcodificar.

**No hace falta ningún MCP ni navegador Chromium** — sería más frágil y complejo para algo que un script local resuelve mejor.

## Quick start

### 1. Grabar muestras en el Mac

```bash
# Dependencias (una vez)
brew install portaudio
pip3 install sounddevice soundfile numpy

# Grabar (repite por persona)
python3 infrastructure/voice/speaker-id/record_samples.py --speaker miguel --count 10
python3 infrastructure/voice/speaker-id/record_samples.py --speaker ana --count 10
```

Genera `infrastructure/voice/speaker-id/samples/<persona>/clip_NN.wav`.

> Alternativa sin `sounddevice` (si tienes `ffmpeg`):
> ```bash
> ffmpeg -f avfoundation -i ":0" -ar 16000 -ac 1 -t 4 samples/miguel/clip_01.wav
> ```

### 2. Subir `samples/` a Google Drive

Copia la carpeta `samples/` a `MyDrive/wayne-speaker-id/samples/` (arrastra en [drive.google.com](https://drive.google.com) o Google Drive para escritorio). Son pocos MB.

### 3. Entrenar y exportar

**Opción A — En tu Mac (recomendado, sin Colab):**

```bash
pip3 install sherpa-onnx soundfile numpy
python3 infrastructure/voice/speaker-id/train_profiles.py
```

Genera todo en `infrastructure/voice/speaker-id/export/` (JSON + modelo + ZIP).

**Opción B — Notebook Colab:**

1. Abre [`notebooks/train_speaker_profiles.ipynb`](notebooks/train_speaker_profiles.ipynb) con kernel **Google Colab**.
2. Ejecuta celdas 1–5a (monta Drive, importa muestras).
3. Ejecuta celdas 6–9 (centroides, umbral, export).
4. Los artefactos quedan en **Google Drive** → `MyDrive/wayne-speaker-id/export/` (no en tu Mac ni en Cursor).

> `files.download()` del notebook **no funciona desde Cursor** — usa Drive o `train_profiles.py` local.

## Estructura de muestras

```
samples/
├── miguel/
│   ├── clip_01.wav
│   └── clip_02.wav
└── ana/
    ├── clip_01.wav
    └── clip_02.wav
```

**Recomendaciones:**
- 8–12 clips por persona, ~4 s cada uno
- Frases variadas en español (no solo "Mariano") — el script sugiere frases
- Incluir clips grabados con el **Satellite1** si es posible (mejor calidad en producción)
- Mezclar condiciones: silencio, TV de fondo, distintas distancias al micrófono

## Artefactos exportados

| Archivo | Destino en HAOS |
|---------|-----------------|
| `speaker_profiles.json` | `/share/speaker-id/` |
| `wespeaker_en_voxceleb_resnet34.onnx` | `/share/speaker-id/` |
| `config.json` | `/share/speaker-id/` (referencia) |

## Validar perfiles localmente

```bash
python3 infrastructure/voice/speaker-id/validate_profiles.py \
  /path/to/speaker_profiles.json
```

## Modelo

Usamos `wespeaker_en_voxceleb_resnet34.onnx` de [sherpa-onnx speaker models](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models).

El mismo archivo ONNX debe estar en Colab y en `/share/speaker-id/` del add-on para que los embeddings sean compatibles.

## Tests

```bash
cd home-assistant/addons/speaker-id-mariano
python3 -m pytest tests/ -v
```

Ver runbook completo: [docs/speaker-id-mariano.md](../../docs/speaker-id-mariano.md)
