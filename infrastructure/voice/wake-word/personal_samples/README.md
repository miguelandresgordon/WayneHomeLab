# Muestras personales — wake word «Mariano»

WAV de captura (Satellite1 / Assist debug), listos para transferir a otro PC.
**No se commitean** (`.gitignore`). Cópialos a USB o `scp` junto con el clone.

## Exportar desde el Mac (antes de borrar TTS/features)

```bash
./infrastructure/voice/wake-word/export_personal_samples.sh
# → infrastructure/voice/wake-word/personal_samples/*.wav
```

Origen por defecto: `~/.taterwakewordtrainer/app/current/personal_samples/`
(clips ya padded a 100 ms). Alternativa cruda: `~/Desktop/mariano_raw/`.

Hay **34 WAV (~2 MB)**. No hace falta zip.

## En Windows 11 (este lab: RX 6750 XT)

1. Copia esta carpeta al clone del repo en el PC (USB / `scp`).
2. `.\infrastructure\voice\wake-word\probe_trainer_windows.ps1`
3. `.\infrastructure\voice\wake-word\setup_trainer_windows.ps1 -Cpu`
4. `.\infrastructure\voice\wake-word\train_mariano_windows.ps1 -Cpu`

Los scripts copian los WAV a `%USERPROFILE%\mww-data\personal_samples`
(volumen Docker `/data/personal_samples`). **No uses `--gpus all`**: CUDA no aplica en Radeon.
