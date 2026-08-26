# WayneHomelab

Asistente de voz privado («Private Alexa») sobre Raspberry Pi + Home Assistant, con Satellite1 (ESPHome / MicroWakeWord) y STT en la nube (Groq).

## Estado actual (rama `satellite1`)

| Pieza | Realidad |
|-------|----------|
| Core | RPi 5 (`192.168.1.100`) → Proxmox → HAOS VM (`192.168.1.110`) |
| Edge RPi 3b | Pendiente; STT/TTS viven en la VM HAOS |
| Satellite1 | `192.168.1.85`, wake word **Okay Nabu** (objetivo: «Mariano») |
| STT | Groq `whisper-large-v3-turbo` vía HACS `openai_whisper_cloud` |
| TTS | Piper add-on (`core-piper:10200`, `es_ES-davefx-medium`) |
| Conversación | Home Assistant built-in (español) |
| Train wake word | **RunPod GPU Pod** (recomendado) · fallback Windows Docker CPU |

Memoria operativa del agente: [`AGENTS.md`](AGENTS.md). Arquitectura: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Pipeline de voz

```
Satellite1 (Okay Nabu)
  → ESPHome → HA (192.168.1.110:8123)
  → STT: Groq (openai_whisper_cloud)
  → Conversation: HA built-in (ES)
  → TTS: Piper Wyoming
  → Satellite1 speaker
```

## Documentación útil

| Doc | Contenido |
|-----|-----------|
| [AGENTS.md](AGENTS.md) | Estado infra, IPs, fixes Proxmox, pendientes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Topología y flujo de datos |
| [docs/setup-desde-cero-ssd-pi5-haos.md](docs/setup-desde-cero-ssd-pi5-haos.md) | Rebuild Pi5 + Proxmox + HAOS desde SSD |
| [docs/setup-from-scratch-headless.md](docs/setup-from-scratch-headless.md) | Path headless completo (WireGuard, edge) |
| [docs/wake-word-mariano.md](docs/wake-word-mariano.md) | Runbook wake word «Mariano» |
| [docs/runpod-train-mariano.md](docs/runpod-train-mariano.md) | Train en RunPod (PC) |
| [docs/runpod-train-mariano-movil.md](docs/runpod-train-mariano-movil.md) | Train desde iOS / Safari |
| [docs/speaker-id-mariano.md](docs/speaker-id-mariano.md) | Speaker ID (Colab + add-on) |
| [docs/reservas-dhcp-bombillas-iot.md](docs/reservas-dhcp-bombillas-iot.md) | Reservas DHCP IoT |
| [docs/api-costs.md](docs/api-costs.md) | Costes API |

## Estructura del repo

```
WayneHomeLab/
├── AGENTS.md
├── infrastructure/
│   ├── proxmox/                 # create_haos_vm.sh
│   ├── nodes/core|edge/         # setup host, fix Proxmox cluster
│   ├── provisioning/mac/        # flash SSD headless
│   └── voice/
│       ├── wake-word/           # Mariano (RunPod / Windows / Mac)
│       └── speaker-id/          # perfiles de voz
├── home-assistant/              # YAML modular → Samba /config
│   ├── includes/                # automations, scripts, scenes…
│   └── addons/speaker-id-mariano/
├── voice-pipeline/              # Docker Whisper+Piper (para RPi 3b)
└── docs/
```

## Quick start (operación diaria)

```bash
# Tras reboot inesperado del RPi 5 (rompe pve-cluster vía cloud-init):
scp infrastructure/nodes/core/fix_proxmox_cluster.sh pi@192.168.1.100:/tmp/
ssh -t pi@192.168.1.100 "sudo bash /tmp/fix_proxmox_cluster.sh && sudo qm start 100"
```

Config HA canónica: `home-assistant/` → desplegar a `/config` (Samba). Ver `infrastructure/voice/speaker-id/deploy_speaker_id_ha_config.sh`.

## Entrenar wake word «Mariano»

```bash
cd infrastructure/voice/wake-word
./setup_trainer_runpod.sh --dry-run   # checklist + volume 200 GB
# Guía: docs/runpod-train-mariano.md  ·  móvil: docs/runpod-train-mariano-movil.md
```

Fallback: Windows 11 + Docker CPU (`setup_trainer_windows.ps1 -Cpu`). La RX 6750 XT **no** es CUDA.

## Licencia

MIT
