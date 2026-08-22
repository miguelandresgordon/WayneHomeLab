# Wake word "Mariano" — Runbook WayneHomeLab

Guía operativa para entrenar, desplegar y afinar la wake word personalizada en Satellite1.

## Arquitectura

```
Satellite1 (MicroWakeWord "Mariano" on-device)
  → ESPHome voice_assistant → HA Assist Pipeline
  → Groq Whisper (STT) → Conversation (es) → Piper (TTS)
```

## 1. Entrenar el modelo

El Mac M3 **no tiene disco suficiente** para un train completo (~25–80 GB de TTS, features y negativos). El camino actual es **Windows 11 + Docker**. El trainer de Apple Silicon se mantiene como Plan B.

### Hardware del PC de entrenamiento

| Componente | Este lab |
|------------|----------|
| Placa | Gigabyte B550M DS3H |
| CPU | AMD Ryzen 5 3600 (6c/12t) |
| GPU | **AMD Radeon RX 6750 XT** (RDNA2, gfx1031) |
| RAM | 16 GB (2×8) |
| Fuente | Seasonic CORE GM-650 |
| OS | Windows 11 + Docker Desktop / WSL2 |

**CUDA no aplica.** `--gpus all` y `nvidia-smi` son para NVIDIA. ROCm oficial **no cubre** la RX 6750 XT (gfx1031: Runtime/HIP SDK ❌). DirectML no está en la imagen Tater. El punto de partida en este PC es la **misma imagen Docker en CPU** (`-Cpu` / `--cpu`).

16 GB de RAM es justo: cierra Chrome/juegos y, en `%UserProfile%\.wslconfig`, limita WSL2 (`memory=10GB`). Disco: **≥ ~80 GB libres** la primera vez.

```powershell
cd ...\WayneHomeLab\infrastructure\voice\wake-word
.\probe_trainer_windows.ps1    # GPU/RAM/disco/Docker; debe recomendar CPU
```

### Captura de muestras

1. Di «Okay Nabu… Mariano» al Satellite1 (variando distancia/ruido).
2. Copia WAV STT desde `/share/assist_pipeline/` (Samba: `smb://192.168.1.110/share`) a `~/Desktop/mariano_raw/`.
3. Descarta clips donde el pitido periódico pise la palabra.
4. `train_mariano_local.sh` (Mac) o `export_personal_samples.sh` deja los WAV en `personal_samples/` con **100 ms de silencio al final** si vienen del pipeline Assist. Sin ese padding, `trim_silence.py` puede dejar clips a 0 ms y perder el último fonema.
5. El mensaje `Skipped N: personal_samples/... Trailing silence ≤ 20ms` **no descarta** el WAV: solo significa que no hace falta recortar más silencio.

Las muestras personales **no se commitean**. Viven en:

| Sitio | Rol |
|-------|-----|
| `~/.taterwakewordtrainer/app/current/personal_samples/` | Mac, padded, listas para train |
| `~/Desktop/mariano_raw/` | Captura cruda Assist |
| `infrastructure/voice/wake-word/personal_samples/` | Carpeta de transferencia (gitignored `*.wav`) |

### Liberar disco en el Mac (conservar solo muestras)

```bash
# 1) Exportar WAV al repo (para USB / scp al PC Windows)
./infrastructure/voice/wake-word/export_personal_samples.sh

# 2) Borrar TTS, features, negativos, Piper, .venv, .cache — keep-personal
./infrastructure/voice/wake-word/free_trainer_disk.sh --keep-personal
```

`--keep-personal` borra artefactos regenerables y **conserva** `personal_samples/`. Otros modos: `--resume`, `--aggressive` (ver `--help`).

### A) Método principal — Windows 11 + Docker CPU (este PC: RX 6750 XT)

TensorFlow+CUDA no es fiable en Windows nativo. Usar **Docker Desktop (backend WSL2)** y la imagen [TaterTotterson/microWakeWord-Trainer-Nvidia-Docker](https://github.com/TaterTotterson/microWakeWord-Trainer-Nvidia-Docker) **sin** `--gpus all`. La generación TTS/features ya es sobre todo CPU; el train del modelo MicroWakeWord en Ryzen 5 3600 será más lento que en NVIDIA, pero es el camino que funciona hoy.

```powershell
# En el clone, con personal_samples/*.wav ya copiados desde el Mac
cd ...\WayneHomeLab\infrastructure\voice\wake-word
.\probe_trainer_windows.ps1
.\setup_trainer_windows.ps1 -Cpu     # pull imagen, volumen %USERPROFILE%\mww-data, SIN --gpus
.\train_mariano_windows.ps1 -Cpu     # sincroniza WAV y arranca el contenedor
```

Si un `docker run --gpus all` falló antes: `docker rm -f waynelab-mww-trainer` y vuelve a lanzar con `-Cpu`.

Equivalente en WSL2 / Git Bash:

```bash
./infrastructure/voice/wake-word/setup_trainer_nvidia.sh --cpu
./infrastructure/voice/wake-word/train_mariano_nvidia.sh --cpu
# Solo ver comandos: ./setup_trainer_nvidia.sh --cpu --dry-run
```

### A2) Si en el futuro hay GPU NVIDIA

El mismo script detecta `nvidia-smi` y usa `--gpus all`. RTX 50-series: `-Blackwell` / `--blackwell`. No combines `-Blackwell` con `-Cpu`.

UI: `http://127.0.0.1:8789` → Trainer → wake word **mariano** → language **Spanish** → confirma `personal_samples` → **Start training**.

Artefactos: `%USERPROFILE%\mww-data\trained_wake_words\mariano.{tflite,json}` (en el contenedor: `/data/trained_wake_words/`).

```bash
# Desde Git Bash / WSL, copiar al repo:
WAKEWORD_TRAINER_DATA_DIR="$HOME/mww-data" \
  ./infrastructure/voice/wake-word/copy_model_from_trainer.sh
```

`--network host` **no** se usa: Docker Desktop en Windows necesita `-p 8789:8789`.

### B) Plan B — Mac Apple Silicon (disco ≥ ~25 GB libres)

```bash
cd /Users/miguel/Proyectos/WayneHomeLab
./infrastructure/voice/wake-word/free_trainer_disk.sh
./infrastructure/voice/wake-word/setup_trainer_macos.sh ui   # opcional, :8789
./infrastructure/voice/wake-word/train_mariano_local.sh
tail -f ~/Proyectos/microWakeWord-Trainer-AppleSilicon/training_mariano.log
```

`caffeinate` no basta: el script usa `nohup` + `disown`. Variables: `MWW_MAX_SAMPLES`, `MWW_PERSONAL_SRC`, `--no-copy-personal`, `--foreground`.

### C) Plan C — Google Colab

Notebook [PrismaKisar/micro-wake-word](https://github.com/PrismaKisar/micro-wake-word), `language="Spanish"`. Menos fiable por desconexiones. Útil si Docker CPU en 16 GB RAM hace OOM.

### Artefactos

Tras un train OK:

- Windows/Docker (CPU o NVIDIA): `$HOME/mww-data/trained_wake_words/mariano.{tflite,json}`
- Mac: `~/.taterwakewordtrainer/app/current/trained_wake_words/mariano.{tflite,json}`

```bash
./infrastructure/voice/wake-word/copy_model_from_trainer.sh
# → infrastructure/voice/wake-word/models/
```

## 2. Servir modelo en LAN

```bash
./infrastructure/voice/wake-word/serve_model.sh
# JSON: http://<IP_MAC>:8765/mariano.json
```

Actualizar IP en [`satellite1_mariano_overlay.yaml`](../infrastructure/voice/wake-word/satellite1_mariano_overlay.yaml).

## 3. Flashear Satellite1 con modelo Mariano

1. HA → ESPHome Device Builder → **Take Control** del Satellite1
2. EDIT → añadir bloque de [`satellite1_mariano_overlay.yaml`](../infrastructure/voice/wake-word/satellite1_mariano_overlay.yaml)
3. **INSTALL** (OTA)
4. HA → Dispositivos → Satellite1 → Configuración:
   - Pipeline de voz (Groq + Piper)
   - Wake word: **Mariano**
   - Sensitivity: **Slightly sensitive**

### Calibrar `probability_cutoff`

| Síntoma | Ajuste |
|---------|--------|
| Falsos positivos con TV | Subir cutoff (85% → 92%) |
| No detecta tu voz | Bajar cutoff (85% → 75%) |

Cambiar en YAML → recompilar → flash OTA.

## 4. Automatizaciones TV (HA)

```bash
HA_HOST=192.168.1.110 ./infrastructure/voice/wake-word/deploy_ha_voice_config.sh
```

Automatizaciones en [`automations.yaml`](../home-assistant/includes/automations.yaml):

- `satellite1_mute_tv_playing` — mute al reproducir TV
- `satellite1_unmute_tv_stopped` — unmute tras 5 min parada

Verificar entity_ids de media_player en HA si difieren de:

- `media_player.sony_bravia_4k`
- `media_player.google_tv_streamer`

## 5. Diagnosticar STT ("no me entiende")

`assist_pipeline.debug_recording_dir` activo en [`configuration.yaml`](../home-assistant/configuration.yaml).

1. Reproducir un fallo
2. Escuchar WAV en `/share/assist_pipeline`
3. Clasificar:
   - Audio malo → subir `auto_gain` / `noise_suppression_level` en ESPHome
   - Transcripción mala → revisar idioma es en pipeline Groq
   - Transcripción OK, acción mala → alias/entidades ([`voice_assist.yaml`](../home-assistant/includes/voice_assist.yaml))

**Desactivar debug** tras 2–3 días (comentar bloque `assist_pipeline`).

## Quick wins (sin reentrenar)

- `select.satellite1_c7ffe4_wake_word_sensitivity` → Slightly sensitive
- Automatizaciones TV (ya en repo)
- Exponer entidades con alias español en HA UI

## Referencias

- [FutureProofHomes FAQs](https://docs.futureproofhomes.net/satellite1-faqs/)
- [ESPHome micro_wake_word](https://esphome.io/components/micro_wake_word/)
- [TaterTotterson Trainer Apple Silicon](https://github.com/TaterTotterson/microWakeWord-Trainer-AppleSilicon)
- [TaterTotterson Trainer NVIDIA Docker](https://github.com/TaterTotterson/microWakeWord-Trainer-Nvidia-Docker)
- [CUDA en WSL2](https://learn.microsoft.com/windows/ai/directml/gpu-cuda-in-wsl) (solo si hay NVIDIA)
- [ROCm Windows GPU matrix](https://rocm.docs.amd.com/projects/install-on-windows/en/develop/reference/system-requirements.html) (RX 6750 XT = no soportada)
