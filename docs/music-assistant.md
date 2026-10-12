# Music Assistant (HAOS)

Add-on **Music Assistant 2.10.2** (`d5369777_music_assistant`) en la VM HAOS `192.168.1.110` (4 GB RAM). Integra Spotify y reproduce en **Satellite1** vía Sendspin. UI: `http://192.168.1.110:8095` o panel Ingress en HA.

Smoke: `bash infrastructure/nodes/haos/verify_music_assistant.sh`

## Causa raíz del crash (2026-09-11)

Al arrancar, Smart Fades importaba **PyTorch** y descargaba `beat_this-small0.ckpt`. En la VM de 4 GB (Piper + ESPHome + Samba + Speaker ID) el OOM killer mató el proceso `mass` (`dmesg`: `Out of memory: Killed process … (mass) total-vm:2883396kB`). Supervisor envió SIGTERM (`shutdown requested!`).

Los `TimeoutError: [Errno join] 0` de Chromecast (TV GA / BRAVIA) **no son la causa**: aparecen *después* del stop, cuando `on_unload` llama `disconnect(0)` y pychromecast hace `join(timeout=0)`.

Whisper local (`core_whisper`) estaba en `boot: auto` y competía por RAM. Debe quedar **parado**, `boot: manual` (STT = Groq).

## Configuración de producción

Opciones del add-on (`home-assistant/addons/music-assistant.options.example`):

```yaml
log_level: info
safe_mode: false
```

`log_level: error` oculta el arranque y solo enseña los ERROR de Cast al apagar — no usarlo en diario.

### Providers

| Provider | Estado | Motivo |
|----------|--------|--------|
| Spotify + Spotify Connect | ON | Fuente de música |
| Sendspin (+ Source) | ON | Satellite1 (`3C:0F:02:C7:FF:E4`) |
| Home Assistant | ON | Integración HA |
| Smart Fades | **OFF** | PyTorch; OOM en 4 GB |
| Chromecast | **OFF** | No hace falta para voz; ERROR al shutdown |
| AirPlay | **OFF** | Macs; no es el target de voz |
| DLNA | **OFF** | No usado |
| Loudness Analysis | ON | ReplayGain vía ffmpeg, sin torch |

Reactivar Cast/AirPlay desde MA → Settings → Providers si se quiere música en la tele/Macs. **No reactivar Smart Fades** en esta VM.

### Add-ons que no deben correr a la vez

- `core_whisper`: **stopped**, `boot: manual`
- No subir RAM de HAOS (host RPi 5 ya reparte 4096 + Pi-hole 768 + WG 512)

## Operación

```bash
# Estado / logs
ssh root@192.168.1.110 'ha apps info d5369777_music_assistant'
ssh root@192.168.1.110 'ha apps logs d5369777_music_assistant'

# Reinicio limpio
ssh root@192.168.1.110 'ha apps restart d5369777_music_assistant'
```

Si MA no pasa de start: `safe_mode: true` en opciones del add-on, arrancar, desactivar el provider problemático, volver `safe_mode: false`.

Integración HA (`music_assistant`): se auto-descubre; websocket `homeassistant_system`. No hace falta `ha core restart` tras un restart del add-on.

## Síntomas vs ruido

- `Attempt 1/5 failed:` (Spotify, INFO) — rate-limit/timeout; no tumba el proceso.
- Sendspin `non-compliant client` en Satellite1 — firmware ESPHome legacy vs protocolo Sendspin; warning, no crash. USB bootloader pendiente no bloquea playback.
- Pi-hole: el cutover DNS del router sigue pendiente; HAOS no usa `.53` como DNS del host. Si algún día HAOS apunta a Pi-hole y Spotify falla, ver [troubleshooting MA](https://www.music-assistant.io/faq/troubleshooting/) (adblockers).

## Persistencia

La config de providers vive en el volumen del add-on (`settings.json`), no en YAML de `/config`. No versionar tokens Spotify ni la DB. Backup del add-on desde HA → Copias de seguridad.
