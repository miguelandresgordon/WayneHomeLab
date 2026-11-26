# Spotify por voz y latencia (Music Assistant en el Satellite1)

## Medidas (2026-11-26, `infrastructure/voice/music/spotify_probe.py`)

| Medida | Resultado |
|---|---|
| Búsqueda MA (servicio `music_assistant.search`) | 0,4–0,9 s |
| Respuesta hablada tras «pon …» (búsqueda + elección) | < 0,1 s tras el STT |
| Canción/disco/playlist/artista hasta `playing` | ≤ 3 s |
| «Siguiente»: título nuevo en HA | 0,02–0,03 s (8/8) |
| «Siguiente»: posición avanzando (≈ audio) | 1,96–2,03 s (6/6), 0 reintentos |
| Reintentos «Spotify Rate Limiter» en logs de MA (desde 2026-10-11) | 197; Attempt 2/5 ×48, 3/5 ×36 (≈ 11 s) |

La posición la publica MA cada ~2 s, así que 1,96 s es una cota superior: el
audio arranca en ≤ 2 s cuando Spotify no limita.

## Causa de los 5–10 s

Los cambios lentos coinciden con «Attempt N/5 failed: Spotify Rate Limiter»:
MA reintenta con espera creciente (intento 3 ≈ 11 s). Pasa porque MA usa por
defecto un **Client ID de Spotify compartido** por todos sus usuarios.
Arreglo (gratis, 5 min, solo puede hacerlo el titular de la cuenta): crear una
app en developer.spotify.com y poner su Client ID en MA → Proveedores →
Spotify → Advanced. Pasos: `.autopilot/PRUEBAS-MIGUEL.md` §1 (local).

Descartadas con datos:
- **RAM/CPU**: VM HAOS ≥ 1,79 GB libres, MA ≤ 4,3 % CPU y 411–470 MiB durante 30 min de reproducción.
- **Sendspin «non-compliant»**: aviso de MA por el firmware ESPHome 2026.8.2 (modo transición sin cifrar); no hubo cortes ni retrasos medibles por ello.
- **Smart Fades**: sigue OFF.

## ¿Music Assistant en su propia VM/LXC?

No. Con los números de arriba la VM no tiene presión de memoria (PSI 0) y el
host tiene 1,6 GB libres; separar MA añadiría una VM más que mantener sin
mejorar la latencia, que la marca Spotify (rate limit), no la Pi.

Repetir la medida:

```bash
.venv/bin/python infrastructure/voice/music/spotify_probe.py --uri "library://playlist/52" --presses 6 --use-position
```
