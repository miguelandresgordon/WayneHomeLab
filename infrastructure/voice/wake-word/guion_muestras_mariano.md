# Guion de muestras «Mariano» (reentrenamiento F3c)

Objetivo: que Mariano te oiga **con la radio o la música altas** y que **no**
se despierte con la tele ni con la voz alta en reuniones. No se lanza ningún
entrenamiento desde aquí (RunPod cuesta dinero: lo decides tú).

## Positivos (Alicia y Miguel, cada uno por separado)

Graba con `record_wake_samples.sh <persona> <condición> 10`, de pie donde
estáis normalmente (el MacBook Air junto al Satellite1, que hace de «oreja»):

| Condición | Cómo | Muestras |
|---|---|---|
| `normal` | voz normal, 1–2 m | 10 |
| `lejos` | voz normal, 3–4 m (otra punta del salón) | 10 |
| `voz_alta` | casi gritando, como en una reunión | 5 |
| `radio_alta` | «Mariano, pon la SER» y sube el volumen al 70 % | 10 |
| `musica_alta` | Spotify con música animada al 70 % | 10 |
| `tele` | tele encendida a volumen normal | 5 |

Total ≈ 50 por persona (Alicia: «alicia», Miguel: «miguel»). Di solo
«Mariano», con naturalidad, cambiando un poco la entonación.

## Negativos

```bash
cd infrastructure/voice/wake-word
# Activaciones falsas reales del Satellite1 (TV/conversación) del pipeline:
../../../.venv/bin/python prepare_retrain_negatives.py --false-wakes --transcripts <transcripts.jsonl>
# TV en español, radio hablada y música (ver retrain_negatives.yaml, ~3 h):
../../../.venv/bin/python prepare_retrain_negatives.py --streams
../../../.venv/bin/python prepare_retrain_negatives.py --summary
```

Luego sigue docs/wake-word-mariano.md → «Reentrenamiento F3» (RunPod o PC
Windows en CPU).
