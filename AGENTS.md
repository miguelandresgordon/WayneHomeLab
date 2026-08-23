# WayneHomelab — Workspace Instructions

## Role & Profile

Act as a **Senior Data Engineer / DevOps Engineer** with deep expertise in:

- Infrastructure as Code (IaC), Linux systems administration, and ARM64 architectures
- Container orchestration (Docker Compose), virtualization (Proxmox/KVM), and networking
- Home Assistant ecosystem, Wyoming protocol, and voice pipeline integration
- API integration, cost optimization, and secrets management
- Shell scripting (Bash/Zsh), Python, and YAML-based configuration

All suggestions, code reviews, and implementations must reflect **production-grade quality**: modular, idempotent, secure, and well-documented.

## Architecture Context

This project is a private voice assistant ecosystem ("Private Alexa") running on Raspberry Pi hardware:

- **Core Node (RPi 5)**: Proxmox (PXVIRT) host → Home Assistant OS VM (bridged networking via vmbr0)
- **Edge Node (RPi 3b)**: Not yet set up. Voice pipeline runs inside HAOS VM for now.
- **STT**: Groq API (Whisper large-v3-turbo) via HACS integration `openai_whisper_cloud` — NOT local Whisper
- **TTS**: Piper add-on (Wyoming, `core-piper:10200`, voice `es_ES-davefx-medium`)
- **Conversation**: Home Assistant built-in (Spanish)
- **Wake word**: Okay Nabu on-device (objetivo: MicroWakeWord «Mariano» en **RunPod GPU Pod**; fallback Windows 11 + Docker CPU, RX 6750 XT — CUDA no aplica)
- **Dev Machine**: MacBook Air M3 (ARM64) — no tiene disco para train completo
- **Training PC (Windows 11)**: DHCP | Ryzen 5 3600 + RX 6750 XT, 16 GB RAM (fallback Docker CPU). RunPod: [docs/runpod-train-mariano.md](docs/runpod-train-mariano.md)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed diagrams and data flow.

## Current Infrastructure State

| Component | IP | Details |
|-----------|-----|---------|
| RPi 5 Host (Proxmox) | `192.168.1.100` | hostname `waynelab-core`, user `pi` |
| HAOS VM (VMID 100) | `192.168.1.110` | 4 GB RAM, 64 GB disk, UEFI, `haos_generic-aarch64-13.2` |
| Satellite1 | `192.168.1.85` | MAC `3c:0f:02:c7:ff:e4`, ESPHome encryption key in `.ha-sat1-test` |
| Edge Node (RPi 3b) | `192.168.1.101` | Not operational yet |
| MacBook (dev) | DHCP | — |
| Training PC (Windows 11) | DHCP | Ryzen 5 3600 + RX 6750 XT, 16 GB RAM |

## Known Issues & Fixes

### Proxmox cluster IPC (recurrent after every reboot)
Cloud-init rewrites `/etc/hosts` on each boot, setting `waynelab-core → 127.0.1.1`, which breaks `pve-cluster` and `pvestatd`.

**Fix** (run after every unexpected reboot):
```bash
ssh -t pi@192.168.1.100 "sudo bash /tmp/fix_proxmox_cluster.sh && sudo qm start 100"
```

If the script is missing from `/tmp` (lost after reboot), copy it again:
```bash
scp infrastructure/nodes/core/fix_proxmox_cluster.sh pi@192.168.1.100:/tmp/
```

The fix is in `infrastructure/nodes/core/fix_proxmox_cluster.sh`.

### Permanent cloud-init fix
```bash
ssh -t pi@192.168.1.100 "sudo sed -i 's/^manage_etc_hosts:.*/manage_etc_hosts: false/' /etc/cloud/cloud.cfg"
```

### HAOS VM not starting after Proxmox fix
```bash
ssh -t pi@192.168.1.100 "sudo qm start 100"
```

### SSH to Proxmox host
- User: `pi` (not `root` — root SSH requires key, not configured)
- Always use `ssh -t` for sudo commands

## Voice Pipeline — Current Setup

```
Satellite1 (MicroWakeWord "Okay Nabu")
  → ESPHome → HA (192.168.1.110:8123)
  → STT: Groq API (whisper-large-v3-turbo) via openai_whisper_cloud
  → Conversation: Home Assistant built-in (Spanish)
  → TTS: Piper Wyoming (core-piper:10200, es_ES-davefx-medium)
  → Satellite1 speaker
```

**Key lessons learned:**
- Local Whisper (`tiny-int8`, `base-int8`, `small-int8`) hallucinates badly in Spanish with Satellite1 audio quality — use Groq API instead
- `[object Object]` error in Assist = Safari blocking microphone over HTTP (not a Whisper issue)
- HA confuses entity names with scene names when both share words — avoid scene names like «Salón» if you have an area named the same
- Frases que funcionan: «Enciende la lámpara» (sin área hasta asignar entidad al área en HA)
- Wyoming state «desconocido» en faster-whisper es un bug conocido de HA; no impide que funcione si Whisper muestra `Ready`

## Devices Configured in HA

| Dispositivo | Integración | IP/ID | Notas |
|-------------|-------------|-------|-------|
| Lámpara Xiaomi (yeelink.light.mono6) | Xiaomi Miot Auto (HACS) | IP reservada `.121` | Token en gestor contraseñas |
| Bombilla Antela | Smart Life / Tuya | IP reservada `.122` | Pendiente Local Tuya |
| Satellite1 c7ffe4 | ESPHome | `192.168.1.85` | Wake word: Okay Nabu |
| Sony BRAVIA 4K | Android TV Remote | — | Descubierto automáticamente |
| Google TV Streamer (TV GA) | Android TV Remote | — | Descubierto automáticamente |
| Google Cast / Chromecast | Google Cast | — | 2 dispositivos |

## Home Assistant Add-ons Instalados

| Add-on | Estado | Notas |
|--------|--------|-------|
| Piper | En ejecución | TTS Wyoming, voz `es_ES-davefx-medium` |
| Whisper | Instalado | STT local — NO usado (sustituido por Groq). Detener para ahorrar RAM |
| File Editor | — | Para editar config YAML |
| HACS | — | Xiaomi Miot Auto, openai_whisper_cloud |

## Hardware — RPi 5

- **Carcasa**: oficial blanca y roja con cooler activo (ventilador PWM)
- **SSD**: Samsung 850 EVO 250 GB en carcasa Posugea (USB, LED azul — solo se puede tapar físicamente)
- **Ventilador**: curva personalizada en `/boot/firmware/config.txt`:
  - < 65°C → apagado (silencio)
  - 65–72°C → 30% (muy silencioso)
  - 72–80°C → 59%
  - > 80°C → 100%

## Hardware — Training PC (Windows 11)

- **Placa**: Gigabyte B550M DS3H
- **CPU**: AMD Ryzen 5 3600 3.6 GHz (6c/12t)
- **GPU**: AMD Radeon RX 6750 XT — **no es NVIDIA**. CUDA / `--gpus all` / `nvidia-smi` no aplican. ROCm oficial no cubre gfx1031.
- **RAM**: 16 GB (2×8). Justo para Docker+TTS; cerrar el resto de apps. El SKU HX316C10F es DDR3; B550 es DDR4 — verificar en el PC; lo que importa para el train es la capacidad.
- **Fuente**: Seasonic CORE GM-650 80 Plus Gold
- **Train**: Docker Desktop + WSL2, imagen Tater, **modo CPU** (`setup_trainer_windows.ps1 -Cpu`)

## Automatizaciones HA

| Automatización | Hora | Acciones |
|----------------|------|---------|
| Modo noche | 23:00 | Mute Satellite1, detener Whisper, apagar luces |
| Modo día | 07:30 | Desmute Satellite1, arrancar Whisper |

Ver `home-assistant/includes/automations.yaml`.

## Code Conventions

- **Shell scripts**: POSIX-compatible where possible, `set -euo pipefail` mandatory, functions for modularity, `shellcheck` clean
- **YAML**: 2-space indentation, no tabs, comments for non-obvious values
- **Docker Compose**: Always specify `deploy.resources.limits`, use `.env` for configurable values, pin image tags
- **File naming**: `snake_case` for scripts, `kebab-case` for docs
- **Commits**: Conventional Commits format (`feat:`, `fix:`, `docs:`, `infra:`)

## Secrets Management

- **NEVER** commit secrets, API keys, passwords, or tokens
- Home Assistant secrets go in `home-assistant/secrets.yaml` (gitignored)
- Docker service secrets go in `voice-pipeline/.env` (gitignored)
- Satellite1 ESPHome encryption key: stored in `/Users/miguel/.ha-sat1-test/config/.storage/esphome.encryption_keys` (MAC `3c:0f:02:c7:ff:e4`)
- Groq API key: en la integración `openai_whisper_cloud` de HA (no commitear)
- Always provide `.example` templates documenting required keys
- Reference secrets via `!secret` in HA YAML or `${VAR}` in Docker Compose

## ARM64 Considerations

- All container images must support `linux/arm64` (verify before suggesting)
- HAOS VM: imagen correcta es `haos_generic-aarch64-X.Y.qcow2` (NO `haos_ova`)
- Storage Proxmox: usar `local` (no `local-lvm` que no existe en esta instalación)
- Prefer lightweight/quantized models (e.g., `tiny-int8` for Whisper on RPi 3b)
- Test scripts must account for both `aarch64` (RPi) and `arm64` (macOS) architectures

## Project Structure

```
WayneHomeLab/
├── infrastructure/              # IaC: Proxmox VM scripts, node setup
│   ├── proxmox/                 # VM creation and configuration
│   │   ├── create_haos_vm.sh    # Crea VM HAOS ARM64 (storage=local, disk=64G)
│   │   └── vm.conf
│   └── nodes/
│       ├── core/                # RPi 5 (Proxmox host)
│       │   ├── fix_proxmox_cluster.sh  # Fix cloud-init /etc/hosts bug (frecuente)
│       │   ├── setup_host.sh
│       │   └── sysctl.conf
│       └── edge/                # RPi 3b (no operativo aún)
│   └── voice/
│       ├── wake-word/           # Wake word "Mariano" (RunPod GPU Pod + Windows Docker CPU/NVIDIA)
│       └── speaker-id/          # Identificación de hablante (Colab + add-on HAOS)
├── home-assistant/              # HA configuration (modular !include pattern)
│   ├── configuration.yaml
│   ├── addons/
│   │   └── speaker-id-mariano/  # Add-on identificación de hablante (HAOS VM)
│   ├── includes/
│   │   ├── automations.yaml     # Modo noche/día
│   │   ├── scripts.yaml
│   │   └── sensors.yaml
│   └── secrets.yaml.example
├── voice-pipeline/              # Docker Compose STT/TTS (para RPi 3b cuando esté listo)
│   ├── docker-compose.yaml      # Whisper + Piper Wyoming
│   └── .env.example
└── docs/                        # Arquitectura, guías, costes
    ├── ARCHITECTURE.md
    ├── setup-desde-cero-ssd-pi5-haos.md
    ├── reservas-dhcp-bombillas-iot.md
    └── api-costs.md
```

## Pendiente / Próximos pasos

- [ ] RPi 3b: instalar DietPi + Docker + `voice-pipeline/` (Whisper+Piper) para descargar HA VM
- [ ] Bombilla Antela: configurar Local Tuya con IP `.122`
- [ ] Wake word personalizada «Mariano» — ver [docs/wake-word-mariano.md](docs/wake-word-mariano.md) y `infrastructure/voice/wake-word/`
- [x] Wake word "Mariano": infra en `infrastructure/voice/wake-word/` + runbook `docs/wake-word-mariano.md`
- [x] Captura de muestras personales (34 WAV Assist) + export `export_personal_samples.sh`
- [x] Disco Mac: `free_trainer_disk.sh --keep-personal` (TTS/features borrados; 34 WAV conservados)
- [ ] Entrenar «Mariano» en **RunPod GPU Pod** (recomendado; 1× RTX 4090 Community on-demand)
  - Guía: [docs/runpod-train-mariano.md](docs/runpod-train-mariano.md)
  - Recargar **$20–25** mínimo (o **$50–55** como techo); Auto-pay **OFF**, alerta saldo **$10**
  - Probe/checklist: `setup_trainer_runpod.sh --dry-run`
  - Train + muestras: `train_mariano_runpod.sh` (`runpodctl send` → `/data/personal_samples`)
  - Kill switch: `--stop-after 48h`; **nunca Spot** ni Instant Cluster
  - Artefactos: `runpodctl receive` → `teardown_runpod_trainer.sh` (stop; `--delete-volume` opt-in) → `MWW_RUNPOD_DATA_DIR=$HOME/mww-runpod copy_model_from_trainer.sh`
- [ ] Fallback: Windows 11 + Docker **CPU** (RX 6750 XT; CUDA no aplica)
  - Transferir `infrastructure/voice/wake-word/personal_samples/*.wav` (gitignored, ~2 MB)
  - Probe: `probe_trainer_windows.ps1`
  - Setup: `setup_trainer_windows.ps1 -Cpu` o `setup_trainer_nvidia.sh --cpu`
  - Train: `train_mariano_windows.ps1 -Cpu` o `train_mariano_nvidia.sh --cpu`
  - Si aparece GPU NVIDIA local: omitir `-Cpu` (el script usa `--gpus all`)
- [ ] Flashear Satellite1 con modelo Mariano (Take Control ESPHome + OTA en LAN)
- [ ] Capturar muestras TV/voz y re-entrenar (`run_capture_workflow.sh retrain`)
  - Runbook: [docs/wake-word-mariano.md](docs/wake-word-mariano.md)
  - Scripts: `infrastructure/voice/wake-word/`
  - Entrenamiento: RunPod GPU Pod (`setup_trainer_runpod.sh`); fallback Windows Docker CPU (`setup_trainer_windows.ps1 -Cpu`); Mac solo si hay ≥ ~25 GB libres (`train_mariano_local.sh`)
- [ ] Asignar entidad `Lámpara` al área `Salón` en HA (para frases con «del salón»)
- [ ] Eliminar/renombrar escenas con nombres genéricos que confunden al intent de HA
- [ ] Configurar HTTPS en HA (para usar micrófono desde Safari/navegador)
- [ ] Gemini API como agente de conversación (cuando se quiera NLU más potente)
- [x] Speaker ID (perfiles de voz tipo Alexa): notebook Colab + add-on HAOS + runbook
  - Notebook: `infrastructure/voice/speaker-id/notebooks/train_speaker_profiles.ipynb`
  - Add-on: `home-assistant/addons/speaker-id-mariano/`
  - Runbook: [docs/speaker-id-mariano.md](docs/speaker-id-mariano.md)
- [ ] Enrolar voces de la casa en Colab y desplegar perfiles a `/share/speaker-id/`
- [ ] Instalar add-on `speaker-id-mariano` en HAOS VM y verificar `input_text.current_speaker`
