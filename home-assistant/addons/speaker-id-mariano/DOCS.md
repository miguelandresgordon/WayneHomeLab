# Speaker ID Mariano — Add-on Documentation

## Overview

This add-on runs inside the HAOS VM and identifies household speakers from
Assist pipeline debug WAV files stored under `/share/assist_pipeline`.

It uses the same `sherpa-onnx` WeSpeaker model and profile format as the
Colab enrollment notebook, ensuring compatible embeddings between training
and inference.

## Data flow

```
Satellite1 → Assist pipeline → debug WAV in /share/assist_pipeline
  → HA automation (folder_watcher) → POST /identify
  → input_text.current_speaker + event speaker_identified
```

## Security

- `/identify` only accepts paths under `/share/assist_pipeline`, `/share/speaker-id`, or `/tmp`.
- No secrets are stored in the add-on image; profiles live on `/share`.
- Port 10400 is exposed on the HAOS LAN — restrict via firewall if needed.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `503` / extractor not loaded | Check model ONNX exists at `model_path` |
| Always `desconocido` | Lower `threshold` or re-enroll with Satellite1 clips |
| Wrong person | Raise `margin` or add more enrollment clips |
| Profiles not updating | Call `/reload` after copying new JSON |
| Build fails on Alpine | Use Debian base (`aarch64-base-debian:bookworm`); sherpa-onnx has no musl wheels |

## Logs

View in **Ajustes → Aplicaciones → Speaker ID Mariano → Registro**.
