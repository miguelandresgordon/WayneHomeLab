# Architecture — WayneHomelab

## Network Topology

```mermaid
graph LR
    subgraph LAN["Home Network (192.168.1.0/24)"]
        ROUTER["Router / Gateway<br/>192.168.1.1"]

        subgraph CORE["Core Node — RPi 5"]
            direction TB
            RPI5["RPi 5 Host<br/>192.168.1.100"]
            PVE["Proxmox VE"]
            HAOS_VM["HAOS VM<br/>192.168.1.110"]
            PIHOLE_VM["Pi-hole VM<br/>192.168.1.53"]
            RPI5 --> PVE
            PVE --> HAOS_VM
            PVE --> PIHOLE_VM
        end

        subgraph EDGE["Edge Node — RPi 3b (pending)"]
            direction TB
            RPI3["RPi 3b<br/>192.168.1.101"]
            DOCKER["Docker (futuro)<br/>Whisper + Piper"]
            RPI3 --> DOCKER
        end

        SAT["Satellite1<br/>192.168.1.85"]
        MAC["MacBook Air M3<br/>(Dev)"]

        ROUTER --- CORE
        ROUTER --- EDGE
        ROUTER --- SAT
        ROUTER --- MAC
    end

    GROQ["Groq API<br/>whisper-large-v3-turbo"]
    HAOS_VM -- "HTTPS" --> GROQ
```

## IP Address Assignment

| Device | IP | Hostname | Role |
|--------|----|----------|------|
| RPi 5 Host | 192.168.1.100 | waynelab-core | Proxmox VE host |
| Pi-hole VM (VMID 101) | 192.168.1.53 | pihole | DNS sinkhole (bridged vmbr0); DHCP sigue en router |
| HAOS VM | 192.168.1.110:8123 | homeassistant | Home Assistant (bridged vmbr0) |
| RPi 3b | 192.168.1.101 | waynelab-edge | Edge (no operativo aún) |
| Satellite1 | 192.168.1.85 | — | ESPHome mic + speaker |
| Lámpara Xiaomi | 192.168.1.121 | — | Xiaomi Miot Auto |
| Bombilla Antela | 192.168.1.122 | — | Tuya (pendiente Local Tuya) |
| MacBook | DHCP | — | Development |
| Training PC | DHCP | — | Windows 11, fallback train CPU |

## Voice Pipeline — Current Data Flow

```mermaid
flowchart LR
    A["Satellite1<br/>Okay Nabu"] -->|ESPHome| C["Home Assistant<br/>:8123"]
    C -->|STT| D["Groq Whisper<br/>large-v3-turbo"]
    D --> C
    C -->|Conversation ES| C
    C -->|Wyoming| E["Piper<br/>core-piper:10200"]
    E -->|Audio| A

    style A fill:#e17055,color:#fff
    style C fill:#00b894,color:#fff
    style D fill:#6c5ce7,color:#fff
    style E fill:#0984e3,color:#fff
```

### Flow detail

1. **Wake word** — Satellite1 detecta «Okay Nabu» on-device (objetivo: MicroWakeWord «Mariano»).
2. **STT** — Audio a HA → integración `openai_whisper_cloud` → Groq. Whisper local en HA está **parado** (alucina en español con audio Satellite1).
3. **NLU** — Conversation agent built-in de HA (español). Gemini queda como mejora futura.
4. **TTS** — Piper Wyoming (`es_ES-davefx-medium`) en el add-on.
5. **Salida** — Audio de vuelta al speaker del Satellite1.

### Ports

| Service | Port | Notes |
|---------|------|-------|
| Home Assistant | 8123 | HTTP LAN (HTTPS pendiente) |
| Pi-hole DNS | 53/tcp+udp | VM `192.168.1.53` (tras cutover router) |
| Pi-hole Admin | 80 | `http://192.168.1.53/admin` |
| Piper Wyoming | 10200 | Add-on HAOS |
| Proxmox UI | 8006 | Host RPi 5 |
| SSH host | 22 | user `pi` |
| RunPod trainer UI | 8789 | Solo durante train Mariano |

## Wake word training (Mariano)

```mermaid
flowchart TB
    SAMPLES["personal_samples/*.wav<br/>~34 WAV Assist"] --> RP["RunPod GPU Pod<br/>imagen Tater + volume /data"]
    SAMPLES --> WIN["Fallback: Windows Docker CPU"]
    RP --> MODEL["mariano.tflite + mariano.json"]
    WIN --> MODEL
    MODEL --> FLASH["OTA Satellite1<br/>ESPHome overlay"]
```

- Guía PC: [runpod-train-mariano.md](runpod-train-mariano.md)
- Guía móvil: [runpod-train-mariano-movil.md](runpod-train-mariano-movil.md)
- Runbook: [wake-word-mariano.md](wake-word-mariano.md)
- Volume recomendado: **200 GB** (100 GB se llena al extraer AudioSet sin cleanup)

## Home Assistant config layout

YAML canónico en el repo → Samba `/config`:

| Repo | Destino HAOS |
|------|----------------|
| `home-assistant/configuration.yaml` | `/config/configuration.yaml` |
| `home-assistant/includes/*.yaml` | `/config/*.yaml` (o includes según `configuration.yaml`) |
| `home-assistant/themes/` | `/config/themes/` |

Entity IDs reales documentados en `AGENTS.md` y `includes/scripts.yaml`.

## Design decisions

| Decision | Rationale |
|----------|-----------|
| Groq STT vs Whisper local | Calidad ES con mic Satellite1; Whisper tiny/base/small alucina |
| Piper en HAOS vs edge | Edge RPi 3b aún no operativo; un solo nodo menos latencia de red |
| Pi-hole en VM propia | DNS aislado de HAOS; 768 MiB en host 8 GB; DHCP permanece en el router |
| RunPod para Mariano | Mac sin disco; Windows solo AMD (sin CUDA); GPU on-demand puntual |
| Network volume 200 GB | Primer train con AudioSet+FMA+CHiME supera 100 GB si no se borran tars |
| No Spot / Instant Cluster | Preemption o multi-nodo innecesario para MicroWakeWord |

## Related docs

- [setup-desde-cero-ssd-pi5-haos.md](setup-desde-cero-ssd-pi5-haos.md)
- [setup-from-scratch-headless.md](setup-from-scratch-headless.md)
- [pihole.md](pihole.md)
- [speaker-id-mariano.md](speaker-id-mariano.md)
- [api-costs.md](api-costs.md)
- [reservas-dhcp-bombillas-iot.md](reservas-dhcp-bombillas-iot.md)
