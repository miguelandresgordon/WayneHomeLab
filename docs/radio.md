# Radio en el Satellite1 — rutas, cortes y medidas

Medido el 2026-11-26 con `infrastructure/voice/radio/radio_probe.py` (estado
del reproductor cada segundo, volumen temporal 0,15). Criterio de «hecho»:
arranque ≤ 8 s y **0 cortes** en ≥ 30 min.

| Ruta | Emisora | Duración | Arranque | Cortes |
|---|---|---|---|---|
| ESPHome + proxy ffmpeg de HA (antes) | SER | 10 min | 1,07 s | 1 (a 96,7 s, no volvió en 503 s) |
| ESPHome + proxy ffmpeg de HA (repetición) | SER | 3,3 min | 1,04 s | 1 (a 173 s) |
| Music Assistant (Sendspin) | SER | **30 min** | 1,74 s | **0** |
| `script.poner_radio` (MA, producción) | SER | 10 min | 1,83 s | 0 |
| `script.poner_radio` (MA, producción) | Radio 3 (HLS) | 5 min | 1,16 s | 0 |

## Causa de los cortes

- **No es el origen**: medido desde el Mac 5 min, hueco máximo 1,27 s (SER),
  0,79 s (RadioVoz), 0,48 s (Filispim).
- **No es el Wi‑Fi**: RSSI del Satellite1 −29…−32 dBm durante todas las pruebas.
- **No es la VM**: ≥ 1,79 GB libres, CPU del core < 7 % (pico 26 % con otra carga).
- **Es el satélite cerrando la conexión con el proxy ffmpeg de HA**: en el
  instante del corte HA registra `ffmpeg transcoding cancelled` (lo emite
  cuando el cliente HTTP cierra). El firmware no deja traza a nivel INFO.
  Upstream FPH tiene arreglos posteriores en el buffer I2S del altavoz y en la
  contabilidad de `speaker_source` (`a07711c`, 2026-10-28) que podrían ser la
  causa; no se aplican por ahora (el firmware está fijado al commit vivo para
  no arriesgar una OTA sin rollback).

## Decisión

`script.reproducir_stream_satellite` reproduce por **Music Assistant**
(`media_player.satellite1`) y solo usa el reproductor ESPHome si MA no está
disponible. Cuesta ~0,7 s más de arranque y elimina los cortes.

Repetir la medida:

```bash
.venv/bin/python infrastructure/voice/radio/radio_probe.py --route script --station ser --duration 1800 --volume 0.15 --max-start-latency 8
```
