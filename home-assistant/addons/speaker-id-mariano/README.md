# Speaker ID Mariano — Home Assistant Add-on

Add-on local que identifica hablantes en comandos de voz del Satellite1.

## Instalación

1. Copia esta carpeta a `/addons/speaker_id_mariano/` en HAOS (Samba o SSH).
2. **Ajustes → Aplicaciones → Tienda de aplicaciones** (esquina inferior derecha).
3. Menú ⋮ (arriba derecha) → **Buscar actualizaciones**.
4. Sección **Aplicaciones locales** → **Speaker ID Mariano** → Instalar.
5. Los perfiles deben estar en `/share/speaker-id/` (ver `deploy_to_haos.sh`).
6. Inicia la app y verifica: `http://<HAOS-IP>:10400/health`

> En HA 2026 los antiguos «Complementos» se llaman **Aplicaciones**. Documentación oficial: [Tutorial: Making your first app](https://developers.home-assistant.io/docs/apps/tutorial/)

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servicio y perfiles cargados |
| POST | `/identify` | `{"path": "/share/assist_pipeline/.../audio.wav"}` |
| POST | `/identify/upload` | Subida multipart de WAV (debug) |
| POST | `/reload` | Recarga `speaker_profiles.json` sin reiniciar |

## Configuración

| Opción | Default | Descripción |
|--------|---------|-------------|
| `threshold` | 0.6 | Score coseno mínimo para aceptar identidad |
| `margin` | 0.05 | Separación mínima entre 1.º y 2.º candidato |
| `profiles_dir` | `/share/speaker-id` | Carpeta con perfiles |
| `model_path` | `/share/speaker-id/wespeaker_en_voxceleb_resnet34.onnx` | Modelo ONNX |
| `num_threads` | 1 | Hilos ONNX (1 recomendado en HAOS VM) |

## Re-enrolar voces

1. Ejecuta el notebook Colab y exporta nuevo `speaker_profiles.json`.
2. Copia a `/share/speaker-id/` vía Samba.
3. `POST http://<HAOS-IP>:10400/reload` o reinicia el add-on.

Ver runbook completo: [docs/speaker-id-mariano.md](../../../docs/speaker-id-mariano.md)
