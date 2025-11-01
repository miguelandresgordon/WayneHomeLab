# Guía de Instalación - Proyecto Charo

## Índice

1. [Requisitos Previos](#requisitos-previos)
2. [Preparación del Hardware](#preparación-del-hardware)
3. [Instalación Raspberry Pi 5](#instalación-raspberry-pi-5)
4. [Instalación Raspberry Pi 4](#instalación-raspberry-pi-4)
5. [Configuración de Home Assistant](#configuración-de-home-assistant)
6. [Configuración de RunPod](#configuración-de-runpod)
7. [Configuración de Dispositivos Smart](#configuración-de-dispositivos-smart)
8. [Verificación y Testing](#verificación-y-testing)

---

## Requisitos Previos

### Hardware Necesario

- ✅ Raspberry Pi 5 (8GB RAM) + fuente alimentación 5V/5A
- ✅ Raspberry Pi 4 Model B (4GB RAM) + fuente alimentación 5V/3A
- ✅ 2x MicroSD cards (32GB+) o mejor: SSD USB para Pi5
- ✅ Webcam USB con micrófono integrado
- ✅ Altavoz Bluetooth (UE BOOM 2 o similar)
- ✅ Router con 2+ puertos Ethernet Gigabit
- ✅ 2x Cables Ethernet Cat6

### Dispositivos Smart Home

- ✅ Bombilla Xiaomi Mi LED Smart Bulb
- ✅ 2x Bombillas Antela/Tuya Smart Bulb
- ✅ TV Sony Bravia (con soporte IP control)

### Cuentas y Servicios

- ✅ Cuenta GitHub (para clonar repo)
- ✅ Cuenta RunPod (con $10+ créditos)
- ✅ Cuenta Mi Home (Xiaomi)
- ✅ Cuenta Smart Life/Tuya

### Software en tu PC

- ✅ Raspberry Pi Imager
- ✅ Terminal SSH (Terminal, PuTTY, etc.)
- ✅ Git
- ✅ Editor de texto (VSCode recomendado)

---

## Preparación del Hardware

### 1. Raspberry Pi OS Installation

#### Para Pi5 (Main Node)

```bash
# Usar Raspberry Pi Imager
# Elegir:
# - OS: Raspberry Pi OS Lite (64-bit) - Debian Bookworm
# - Storage: SSD USB 256GB (recomendado) o SD 32GB+

# Configuración avanzada (Ctrl+Shift+X):
# - Hostname: pi5.local
# - Enable SSH: Yes (with password or key)
# - Username: pi
# - Password: [tu password seguro]
# - WiFi: [configurar red] o usar Ethernet (recomendado)
# - Locale: Europe/Madrid, es_ES
```

#### Para Pi4 (Audio Node)

```bash
# Usar Raspberry Pi Imager
# Elegir:
# - OS: Raspberry Pi OS Lite (64-bit) - Debian Bookworm
# - Storage: SD Card 32GB+

# Configuración avanzada:
# - Hostname: pi4.local
# - Enable SSH: Yes
# - Username: pi
# - Password: [mismo password que Pi5]
# - WiFi: Ethernet recomendado
# - Locale: Europe/Madrid, es_ES
```

### 2. Primera Conexión

```bash
# Conectar ambas Pis via Ethernet al router
# Esperar ~2 minutos para el primer boot

# Conectar via SSH
ssh pi@pi5.local
ssh pi@pi4.local

# Actualizar sistema (en ambas)
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 3. Configuración de Red Estática

#### En Pi5:

```bash
sudo nano /etc/dhcpcd.conf

# Añadir al final:
interface eth0
static ip_address=192.168.1.101/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8

# Guardar y reiniciar
sudo reboot
```

#### En Pi4:

```bash
sudo nano /etc/dhcpcd.conf

# Añadir al final:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8

sudo reboot
```

### 4. Verificar Conectividad

```bash
# Desde tu PC
ping 192.168.1.101  # Pi5
ping 192.168.1.100  # Pi4

# Desde Pi5
ping 192.168.1.100  # Pi4

# Desde Pi4
ping 192.168.1.101  # Pi5
```

---

## Instalación Raspberry Pi 5

### Opción A: Instalación Automática (Recomendado)

```bash
ssh pi@192.168.1.101

# Clonar repositorio temporalmente
git clone https://github.com/tu-usuario/WayneHomeLab.git /tmp/WayneHomeLab
cd /tmp/WayneHomeLab
git checkout charo

# Ejecutar script de instalación
sudo deployment/scripts/install_pi5.sh

# El script hará automáticamente:
# - Actualizar sistema
# - Configurar SSD (si está disponible)
# - Instalar Docker y Docker Compose
# - Configurar Docker para usar SSD
# - Clonar repositorio en ubicación final
# - Copiar archivos .env
# - Construir servicios Docker
# - Configurar auto-inicio con systemd
# - Iniciar todos los servicios
```

**IMPORTANTE**: Después de la instalación automática:
1. Editar `/opt/charo/.env` (o `/mnt/ssd/charo/.env` si usas SSD) con tus valores reales
2. Editar `/opt/charo/services/home-assistant/config/secrets.yaml` con tus credenciales
3. Reiniciar servicios: `cd /opt/charo/deployment/docker && docker compose -f pi5-compose.yml restart`

### Opción B: Instalación Manual

Si prefieres tener más control sobre cada paso:

#### 1. Dependencias Base

```bash
ssh pi@192.168.1.101

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
newgrp docker

# Verificar instalación
docker --version
docker compose version

# Instalar herramientas adicionales
sudo apt install -y \
    git \
    vim \
    htop \
    tmux \
    python3-pip \
    python3-venv \
    postgresql-client \
    redis-tools \
    avahi-utils
```

### 2. Clonar Repositorio

```bash
cd ~
git clone https://github.com/tu-usuario/WayneHomeLab.git
cd WayneHomeLab
git checkout charo

# Verificar estructura
ls -la
```

### 3. Configurar Variables de Entorno

```bash
cd ~/WayneHomeLab
cp .env.example .env
nano .env

# Editar las siguientes variables (mínimo):
HOME_ASSISTANT_TOKEN="[obtener después]"
RUNPOD_API_KEY="[obtener después]"
XIAOMI_BULB_TOKEN="[obtener después]"
TUYA_USERNAME="tu_email@example.com"
TUYA_PASSWORD="tu_password"
SONY_TV_PSK="[obtener después]"
POSTGRES_PASSWORD="[generar password seguro]"
JWT_SECRET="[generar: openssl rand -hex 32]"

# Guardar: Ctrl+O, Enter, Ctrl+X
```

### 4. Generar Secrets

```bash
# Generar JWT secret
openssl rand -hex 32

# Generar password de PostgreSQL
openssl rand -base64 24

# Copiar estos valores al .env
nano .env
```

### 5. Instalar Piper TTS

```bash
# Crear directorio
sudo mkdir -p /opt/piper
cd /opt/piper

# Descargar Piper para ARM64
sudo wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz
sudo tar -xzf piper_arm64.tar.gz
sudo chmod +x piper

# Descargar modelo de voz español
sudo mkdir -p models
cd models
sudo wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx
sudo wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json

# Verificar instalación
/opt/piper/piper --version
```

### 6. Configurar Swap (Recomendado)

```bash
# Aumentar swap para operaciones pesadas
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile

# Cambiar CONF_SWAPSIZE:
CONF_SWAPSIZE=4096

sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 7. Script de Instalación Automática

```bash
cd ~/WayneHomeLab
chmod +x deployment/scripts/install_pi5.sh

# Ejecutar script (cuando esté listo)
# ./deployment/scripts/install_pi5.sh
```

---

## Instalación Raspberry Pi 4

### Opción A: Instalación Automática (Recomendado)

```bash
ssh pi@192.168.1.100

# Clonar repositorio temporalmente
git clone https://github.com/tu-usuario/WayneHomeLab.git /tmp/WayneHomeLab
cd /tmp/WayneHomeLab
git checkout charo

# Ejecutar script de instalación
sudo deployment/scripts/install_pi4.sh

# El script hará automáticamente:
# - Actualizar sistema
# - Instalar Docker y Docker Compose
# - Configurar PulseAudio en modo system
# - Configurar Bluetooth
# - Emparejar altavoz Bluetooth (interactivo)
# - Probar micrófono USB
# - Clonar repositorio en ubicación final
# - Copiar archivos .env
# - Construir audio-service
# - Configurar auto-inicio con systemd
# - Iniciar servicio de audio
```

**IMPORTANTE**: Después de la instalación automática:
1. Editar `/opt/charo/.env` con:
   - `CHARO_CORE_HOST=192.168.1.101` (IP de la Pi5)
   - `BLUETOOTH_MAC=[MAC de tu altavoz]` (obtenida durante el emparejamiento)
2. Reiniciar servicio: `cd /opt/charo/deployment/docker && docker compose -f pi4-compose.yml restart`

### Script de Configuración de Bluetooth

Si necesitas reconfigurar el Bluetooth después:

```bash
cd /opt/charo
sudo deployment/scripts/setup_bluetooth.sh

# Este script te ayudará a:
# - Escanear dispositivos Bluetooth cercanos
# - Emparejar tu altavoz UE BOOM 2
# - Configurar PulseAudio
# - Obtener la MAC address para el .env
```

### Opción B: Instalación Manual

Si prefieres tener más control sobre cada paso:

#### 1. Dependencias Base

```bash
ssh pi@192.168.1.100

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
newgrp docker

# Instalar dependencias de audio
sudo apt install -y \
    git \
    vim \
    pulseaudio \
    pulseaudio-module-bluetooth \
    bluez \
    alsa-utils \
    python3-pip \
    python3-venv \
    libportaudio2 \
    libsndfile1
```

### 2. Configurar PulseAudio

```bash
# Configurar PulseAudio en modo system
sudo nano /etc/pulse/system.pa

# Añadir al final:
load-module module-bluetooth-policy
load-module module-bluetooth-discover
load-module module-bluez5-discover

# Iniciar PulseAudio
pulseaudio --start

# Verificar
pactl info
```

### 3. Configurar Bluetooth

```bash
# Iniciar servicio Bluetooth
sudo systemctl start bluetooth
sudo systemctl enable bluetooth

# Entrar en bluetoothctl
bluetoothctl

# Dentro de bluetoothctl:
power on
agent on
default-agent
scan on

# Esperar a ver tu UE BOOM 2 (algo como: 00:11:22:33:44:55)
# Cuando aparezca:
pair 00:11:22:33:44:55
trust 00:11:22:33:44:55
connect 00:11:22:33:44:55

# Si pide PIN, probar: 0000 o 1234
# Salir
quit

# Verificar conexión
pactl list short sinks
# Debe aparecer bluez_sink.UE_BOOM_2 o similar
```

### 4. Test de Audio

```bash
# Instalar herramienta de test
sudo apt install -y sox

# Test micrófono
arecord -D hw:1,0 -d 5 -f cd test_mic.wav
aplay test_mic.wav

# Test altavoz Bluetooth
speaker-test -D bluez_sink.UE_BOOM_2 -c 2 -t wav
```

### 5. Clonar Repositorio

```bash
cd ~
git clone https://github.com/tu-usuario/WayneHomeLab.git
cd WayneHomeLab
git checkout charo
```

### 6. Configurar Variables de Entorno

```bash
cd ~/WayneHomeLab
cp .env.example .env
nano .env

# Configurar específico de Pi4:
PI4_HOST="192.168.1.100"
PI5_HOST="192.168.1.101"
BLUETOOTH_SPEAKER_MAC="00:11:22:33:44:55"  # Tu MAC real
AUDIO_INPUT_DEVICE="USB Webcam"  # Verificar nombre real

# Guardar
```

### 7. Entrenar Wake Word

```bash
# Crear directorio de samples
mkdir -p ~/WayneHomeLab/samples

# Grabar muestras (repetir 5-10 veces)
arecord -D hw:1,0 -d 3 -f cd samples/wayne_oye_charo_1.wav
arecord -D hw:1,0 -d 3 -f cd samples/wayne_oye_charo_2.wav
# ...

# Cuando esté listo el script de training:
# cd ~/WayneHomeLab
# python tools/train_wake_word.py --samples samples/
```

---

## Configuración de Home Assistant

### 1. Instalación con Docker (en Pi5)

```bash
ssh pi@192.168.1.101

# Crear directorios
mkdir -p ~/homeassistant/config

# Ejecutar Home Assistant
docker run -d \
  --name homeassistant \
  --privileged \
  --restart=unless-stopped \
  -e TZ=Europe/Madrid \
  -v ~/homeassistant/config:/config \
  -v /run/dbus:/run/dbus:ro \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable

# Verificar logs
docker logs -f homeassistant

# Esperar ~2 minutos para el primer inicio
```

### 2. Acceso Web

```bash
# Desde tu navegador:
http://192.168.1.101:8123

# Completar wizard:
# - Nombre: Wayne
# - Usuario: wayne
# - Password: [tu password]
# - Ubicación: [tu dirección]
# - Zona horaria: Europe/Madrid
# - Sistema métrico: Sí
```

### 3. Crear Long-Lived Access Token

```bash
# En Home Assistant web:
# 1. Click en tu perfil (abajo izquierda)
# 2. Scroll hasta "Tokens de larga duración"
# 3. Crear token: "Charo Voice Assistant"
# 4. Copiar el token (solo se muestra una vez!)

# Añadir al .env en Pi5:
nano ~/WayneHomeLab/.env
# HOME_ASSISTANT_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### 4. Copiar Configuración

```bash
# En Pi5
cd ~/WayneHomeLab
cp services/home-assistant/config/configuration.yaml \
   ~/homeassistant/config/configuration.yaml

cp services/home-assistant/config/secrets.yaml.example \
   ~/homeassistant/config/secrets.yaml

# Editar secrets
nano ~/homeassistant/config/secrets.yaml
```

### 5. Reiniciar Home Assistant

```bash
docker restart homeassistant

# Verificar logs
docker logs -f homeassistant
```

---

## Configuración de RunPod

### 1. Crear Cuenta

```bash
# Ir a: https://runpod.io
# Registrarse con email
# Verificar email
# Añadir método de pago
# Añadir $10-20 de crédito
```

### 2. Obtener API Key

```bash
# En RunPod dashboard:
# 1. Settings > API Keys
# 2. Create API Key: "Charo Voice Assistant"
# 3. Copiar la key

# Añadir al .env:
nano ~/WayneHomeLab/.env
# RUNPOD_API_KEY="your_key_here"
```

### 3. Crear Serverless Endpoint - Whisper

```bash
# En RunPod dashboard:
# 1. Serverless > Create Endpoint
# 2. Nombre: "charo-whisper"
# 3. Docker Image: runpod/faster-whisper:latest
# 4. GPU: RTX 3090 (mejor precio/rendimiento)
# 5. Min Workers: 0 (scale to zero)
# 6. Max Workers: 1
# 7. Idle Timeout: 60s
# 8. Container Disk: 10GB
# 9. Environment Variables:
#    - MODEL_NAME=medium
#    - LANGUAGE=es
# 10. Create

# Copiar Endpoint ID y URL
# Añadir al .env
nano ~/WayneHomeLab/.env
# RUNPOD_WHISPER_ENDPOINT="https://api.runpod.ai/v2/xxx"
```

### 4. Crear Serverless Endpoint - LLM

```bash
# En RunPod dashboard:
# 1. Serverless > Create Endpoint
# 2. Nombre: "charo-llm"
# 3. Docker Image: vllm/vllm-openai:latest
# 4. GPU: RTX 3090
# 5. Min Workers: 0
# 6. Max Workers: 1
# 7. Idle Timeout: 60s
# 8. Container Disk: 20GB
# 9. Environment Variables:
#    - MODEL=TheBloke/Mistral-7B-Instruct-v0.2-GGUF
#    - QUANTIZATION=Q4_K_M
# 10. Create

# Copiar Endpoint ID
# Añadir al .env
nano ~/WayneHomeLab/.env
# RUNPOD_LLM_ENDPOINT="https://api.runpod.ai/v2/yyy"
```

### 5. Verificar Endpoints

```bash
# Test Whisper
curl -X POST "https://api.runpod.ai/v2/xxx/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"audio": "base64_encoded_audio"}}'

# Test LLM
curl -X POST "https://api.runpod.ai/v2/yyy/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "Hola, ¿cómo estás?"}}'
```

---

## Configuración de Dispositivos Smart

### 1. Xiaomi Mi LED Smart Bulb

#### Obtener Token

```bash
# Opción 1: Xiaomi Cloud Tokens Extractor
# https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor

# Instalar en tu PC:
pip install micloud

# Ejecutar:
micloud

# Ingresar credenciales Mi Home
# Copiar el token de tu bombilla

# Opción 2: python-miio
pip install python-miio
miiocli cloud

# Copiar token
```

#### Configurar IP Estática

```bash
# En la app Mi Home:
# 1. Seleccionar bombilla
# 2. Configuración > Red
# 3. Configurar IP estática: 192.168.1.110
```

#### Test

```bash
# En Pi5
pip install python-miio

# Test conexión
miiocli device --ip 192.168.1.110 --token YOUR_TOKEN info

# Test encender/apagar
miiocli yeelight --ip 192.168.1.110 --token YOUR_TOKEN on
miiocli yeelight --ip 192.168.1.110 --token YOUR_TOKEN off
```

---

### 2. Bombillas Tuya/Antela

#### Configurar en App

```bash
# 1. Descargar app "Smart Life" o "Tuya Smart"
# 2. Registrarse con email
# 3. Añadir bombillas siguiendo wizard
# 4. Anotar nombres de dispositivos
```

#### Obtener Credenciales

```bash
# Usar las credenciales de la app directamente
# Usuario: tu_email@example.com
# Password: tu_password

# Añadir al .env y secrets.yaml
```

#### Configurar IPs Estáticas (opcional)

```bash
# En router, asignar IPs fijas a MACs de bombillas:
# Bombilla 1: 192.168.1.111
# Bombilla 2: 192.168.1.112
```

---

### 3. Sony Smart TV

#### Activar Control IP

```bash
# En la TV:
# 1. Configuración > Red
# 2. Configuración de red avanzada
# 3. Autenticación y control de acceso IP
# 4. Método de autenticación: Pre-Shared Key
# 5. Pre-Shared Key: [crear un PSK de 4 dígitos, ej: 1234]
# 6. Inicio de sesión simple de IP: Activado
```

#### Configurar IP Estática

```bash
# En la TV:
# 1. Configuración > Red
# 2. Configurar red
# 3. Manual
# 4. IP: 192.168.1.120
# 5. Máscara: 255.255.255.0
# 6. Gateway: 192.168.1.1
# 7. DNS: 8.8.8.8
```

#### Test

```bash
# Instalar braviaproapi
pip install pybravia

# Test desde Pi5
python3 << EOF
from pybravia import BraviaClient

client = BraviaClient("192.168.1.120", psk="1234")
print(client.get_power_status())
EOF
```

---

## Verificación y Testing

### 1. Verificar Servicios en Pi5

```bash
ssh pi@192.168.1.101

# Docker
docker ps

# PostgreSQL (cuando se levante)
docker exec -it postgres psql -U charo_user -d charo_db -c "\l"

# Redis (cuando se levante)
docker exec -it redis redis-cli ping

# Home Assistant
curl http://localhost:8123/api/

# Piper TTS
/opt/piper/piper --help
```

### 2. Verificar Servicios en Pi4

```bash
ssh pi@192.168.1.100

# Bluetooth
pactl list short sinks | grep bluez

# Micrófono
arecord -l

# Test audio end-to-end
arecord -D hw:1,0 -d 3 -f cd test.wav
aplay -D bluez_sink.UE_BOOM_2 test.wav
```

### 3. Test de Conectividad

```bash
# Desde Pi5 a Home Assistant
curl -H "Authorization: Bearer $HOME_ASSISTANT_TOKEN" \
  http://localhost:8123/api/states | jq .

# Desde Pi5 a RunPod
curl -X POST "https://api.runpod.ai/v2/xxx/health" \
  -H "Authorization: Bearer $RUNPOD_API_KEY"

# Desde Pi5 a dispositivos
# Xiaomi
ping 192.168.1.110

# Sony TV
ping 192.168.1.120
```

### 4. Test Home Assistant Integrations

```bash
# En Home Assistant web (http://192.168.1.101:8123):

# 1. Developer Tools > Services
# 2. Test luces Xiaomi:
#    Service: light.turn_on
#    Entity: light.xiaomi_bulb
#    [Call Service]

# 3. Test luces Tuya:
#    Service: light.turn_on
#    Entity: light.antela_bulb_1

# 4. Test TV Sony:
#    Service: media_player.turn_on
#    Entity: media_player.tv_sony
```

### 5. Smoke Test Completo

```bash
cd ~/WayneHomeLab

# Crear script de test
cat > test_integration.sh << 'EOF'
#!/bin/bash
echo "🔍 Testing Charo Integration..."

echo "✓ Ping Pi4"
ping -c 1 192.168.1.100

echo "✓ Ping Pi5"
ping -c 1 192.168.1.101

echo "✓ Test Home Assistant"
curl -s http://192.168.1.101:8123/api/ | grep "API running"

echo "✓ Test Xiaomi bulb"
ping -c 1 192.168.1.110

echo "✓ Test Sony TV"
ping -c 1 192.168.1.120

echo "✅ All tests passed!"
EOF

chmod +x test_integration.sh
./test_integration.sh
```

---

## Próximos Pasos

Una vez completado este setup:

1. ✅ Revisar que todos los tests pasan
2. ✅ Verificar que el archivo `.env` está completo
3. ✅ Documentar las IPs y MACs de tus dispositivos
4. ✅ Hacer backup de tokens y secrets
5. ➡️ Proceder a implementar los servicios Python (Fase 1)

Ver [ARCHITECTURE.md](ARCHITECTURE.md) para detalles de implementación.

---

## Troubleshooting Rápido

### Home Assistant no inicia
```bash
docker logs homeassistant
# Verificar permisos: sudo chown -R 1000:1000 ~/homeassistant
```

### Bluetooth no conecta
```bash
sudo systemctl restart bluetooth
bluetoothctl
power off
power on
connect [MAC]
```

### No se obtiene token Xiaomi
```bash
# Usar método alternativo:
# https://github.com/rytilahti/python-miio/issues/1095
```

### RunPod timeout
```bash
# Aumentar idle_timeout en endpoint settings
# O implementar keep-alive (ver Fase 3)
```

---

*Última actualización: Enero 2025*
