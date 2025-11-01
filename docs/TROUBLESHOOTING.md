# Troubleshooting - Proyecto Charo

Guía de solución de problemas comunes durante desarrollo y operación del proyecto.

## Índice

1. [Problemas de Setup](#problemas-de-setup)
2. [Problemas de Audio](#problemas-de-audio)
3. [Problemas de Red](#problemas-de-red)
4. [Problemas de Home Assistant](#problemas-de-home-assistant)
5. [Problemas de RunPod](#problemas-de-runpod)
6. [Problemas de Python/Tests](#problemas-de-pythontests)
7. [Problemas de Docker](#problemas-de-docker)
8. [Problemas de Rendimiento](#problemas-de-rendimiento)

---

## Problemas de Setup

### Python version incorrecta

**Síntoma**: `SyntaxError` o `ModuleNotFoundError` al ejecutar el código

**Causa**: Python < 3.11

**Solución**:
```bash
# Verificar versión actual
python --version

# Si es < 3.11, instalar con pyenv
pyenv install 3.11.7
pyenv local 3.11.7
python --version  # Verificar
```

---

### pip install falla con errores de compilación

**Síntoma**: Error al instalar dependencias con `pip install -r requirements.txt`

**Causa**: Faltan headers de desarrollo en el sistema

**Solución**:
```bash
# Raspberry Pi OS / Debian
sudo apt install -y python3-dev build-essential libffi-dev libssl-dev

# macOS
xcode-select --install

# Reintentar instalación
pip install -r requirements.txt
```

---

### Import errors en tests

**Síntoma**: `ModuleNotFoundError: No module named 'charo_core'`

**Causa**: Paths de Python no configurados correctamente

**Solución**:
```bash
# Opción 1: Instalar en modo editable
cd services/charo-core
pip install -e .

# Opción 2: Agregar a pyproject.toml
# [tool.pytest.ini_options]
# pythonpath = ["src"]

# Opción 3: PYTHONPATH manual
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/
```

---

## Problemas de Audio

### Micrófono no detectado

**Síntoma**: `arecord -l` no muestra la webcam USB

**Solución**:
```bash
# Verificar que está conectada
lsusb  # Debe aparecer la webcam

# Recargar módulos de audio
sudo modprobe snd-usb-audio

# Verificar permisos
sudo usermod -aG audio $USER
newgrp audio

# Verificar de nuevo
arecord -l
```

---

### Altavoz Bluetooth no conecta

**Síntoma**: UE BOOM 2 no aparece en `bluetoothctl`

**Solución**:
```bash
# Asegurar que el altavoz está en modo pairing (botón Bluetooth)
# Reiniciar servicio Bluetooth
sudo systemctl restart bluetooth

# Entrar en bluetoothctl
bluetoothctl

# Dentro de bluetoothctl
power off
power on
scan on
# Esperar a ver el dispositivo
pair [MAC_ADDRESS]
trust [MAC_ADDRESS]
connect [MAC_ADDRESS]

# Si sigue fallando, borrar y re-emparejar
remove [MAC_ADDRESS]
# Repetir pairing
```

---

### Audio de mala calidad o entrecortado

**Síntoma**: Audio con ruido, cortes o lag

**Solución**:
```bash
# Aumentar buffer de PulseAudio
nano ~/.config/pulse/daemon.conf

# Añadir/modificar:
default-fragment-size-msec = 25
default-fragments = 4

# Reiniciar PulseAudio
pulseaudio --kill
pulseaudio --start

# Verificar latencia
pactl list sinks | grep -i latency
```

---

### Wake word no detecta "Oye, Charo"

**Síntoma**: OpenWakeWord no se activa al decir la frase

**Solución**:
```bash
# 1. Verificar threshold (puede estar muy alto)
# Editar configuración y bajar threshold a 0.3
nano services/audio-service/src/wake_word_config.py
# WAKE_WORD_THRESHOLD = 0.3  # Era 0.5

# 2. Verificar ganancia de audio
# Puede ser necesario amplificar la señal
# AUDIO_GAIN = 2.0  # Era 1.5

# 3. Test de audio directo
python tools/test_audio.py --device "USB Webcam"

# 4. Entrenar modelo personalizado
python tools/train_wake_word.py --samples samples/
```

---

### False positives del wake word

**Síntoma**: Se activa sin decir "Oye, Charo"

**Solución**:
```bash
# Subir threshold
nano services/audio-service/src/wake_word_config.py
# WAKE_WORD_THRESHOLD = 0.7  # Era 0.5

# Añadir samples negativos (frases similares que NO deben activar)
python tools/train_wake_word.py \
  --samples samples/ \
  --negative-samples samples/negative/
```

---

## Problemas de Red

### No se puede hacer ping entre Pis

**Síntoma**: `ping 192.168.1.101` desde Pi4 falla

**Solución**:
```bash
# Verificar IPs asignadas
ip addr show

# Verificar que están en la misma subnet
# Pi4: 192.168.1.100/24
# Pi5: 192.168.1.101/24

# Verificar firewall
sudo iptables -L

# Si hay reglas que bloquean, limpiar temporalmente
sudo iptables -F

# Verificar conectividad a gateway
ping 192.168.1.1
```

---

### WebSocket no conecta entre Pi4 y Pi5

**Síntoma**: Error de conexión en logs de audio-service

**Solución**:
```bash
# En Pi5: Verificar que el servicio está escuchando
sudo netstat -tulpn | grep 8082
# Debe aparecer: tcp 0.0.0.0:8082 LISTEN

# Si no está escuchando, verificar firewall
sudo ufw status
sudo ufw allow 8082/tcp

# Verificar conectividad
telnet 192.168.1.101 8082
# Debe conectar

# Verificar logs del servicio
docker logs charo-core | grep -i websocket
```

---

## Problemas de Home Assistant

### No se obtiene token de acceso

**Síntoma**: No puedes crear long-lived access token

**Solución**:
1. Acceder a Home Assistant: `http://192.168.1.101:8123`
2. Login con tus credenciales
3. Click en tu perfil (esquina inferior izquierda)
4. Scroll hasta "Tokens de larga duración"
5. Click "Crear token"
6. Nombrar: "Charo Voice Assistant"
7. **COPIAR INMEDIATAMENTE** (solo se muestra una vez)
8. Guardar en `.env`:
   ```bash
   HOME_ASSISTANT_TOKEN="eyJ0eXAiOiJ..."
   ```

---

### Bombilla Xiaomi no se añade

**Síntoma**: Error al añadir bombilla en `configuration.yaml`

**Solución**:
```bash
# 1. Obtener token de la bombilla
pip install micloud

# Ejecutar en Python
python3 << EOF
from micloud import MiCloud
mc = MiCloud("tu_email@mi.com", "tu_password")
mc.login()
devices = mc.get_devices()
for device in devices:
    if "yeelight" in device["model"]:
        print(f"Token: {device['token']}")
        print(f"IP: {device['localip']}")
EOF

# 2. Configurar IP estática en app Mi Home
# Settings > Device > Network

# 3. Test conexión
pip install python-miio
miiocli device --ip 192.168.1.110 --token YOUR_TOKEN info

# 4. Agregar a configuration.yaml
nano ~/homeassistant/config/configuration.yaml
```

---

### Sony TV no responde a comandos

**Síntoma**: Error al intentar encender/apagar TV

**Solución**:
```bash
# 1. Verificar PSK configurado en la TV
# TV: Settings > Network > IP Control > Pre-Shared Key

# 2. Verificar conectividad
ping 192.168.1.120

# 3. Test con pybravia
pip install pybravia
python3 << EOF
from pybravia import BraviaClient
client = BraviaClient("192.168.1.120", psk="1234")
print(client.get_power_status())
EOF

# 4. Si falla, regenerar PSK en la TV
# Y actualizar en secrets.yaml
```

---

### Home Assistant no inicia en Docker

**Síntoma**: `docker logs homeassistant` muestra errores

**Solución**:
```bash
# Verificar permisos del directorio config
ls -la ~/homeassistant/
sudo chown -R 1000:1000 ~/homeassistant/

# Verificar que no hay errores en configuration.yaml
docker run --rm -v ~/homeassistant/config:/config \
  ghcr.io/home-assistant/home-assistant:stable \
  python -m homeassistant --script check_config --config /config

# Ver logs detallados
docker logs -f homeassistant

# Reiniciar container
docker restart homeassistant
```

---

## Problemas de RunPod

### Cold start muy lento (>30s)

**Síntoma**: Primera petición a RunPod tarda mucho

**Solución**:
```python
# Implementar keep-alive en charo-core
# services/charo-core/src/runpod_keepalive.py

import asyncio
import aiohttp

async def keep_alive_task():
    """Keep RunPod endpoints warm."""
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{RUNPOD_WHISPER_ENDPOINT}/health",
                    headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"}
                )
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
        await asyncio.sleep(300)  # Cada 5 minutos
```

---

### RunPod timeout / API errors

**Síntoma**: `TimeoutError` o `502 Bad Gateway` de RunPod

**Solución**:
```bash
# 1. Verificar status de RunPod
curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
  https://api.runpod.ai/v2/YOUR_ENDPOINT/health

# 2. Aumentar timeout en cliente
nano services/charo-core/src/runpod_client.py
# RUNPOD_TIMEOUT = 60000  # Era 30000

# 3. Implementar retry con exponential backoff
# Agregar a runpod_client.py:
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_runpod_api(...):
    ...
```

---

### RunPod costs too high

**Síntoma**: Factura mensual > 20€

**Solución**:
```bash
# 1. Verificar uso real en RunPod dashboard
# Usage > Analytics > Last 30 days

# 2. Reducir idle_timeout de endpoints
# Settings > Endpoint > idle_timeout = 30s (era 60s)

# 3. Implementar cache más agresivo
# Aumentar TTL en Redis
nano .env
# CACHE_TTL_COMMANDS=7200  # 2 horas (era 1 hora)

# 4. Filtrar comandos simples localmente
# No enviar a RunPod comandos que se pueden resolver con patterns
```

---

## Problemas de Python/Tests

### Tests fallan con "Event loop closed"

**Síntoma**: Tests asyncio fallan con error de event loop

**Solución**:
```python
# Opción 1: Usar pytest-asyncio correctamente
# Agregar a conftest.py
import pytest

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Opción 2: Usar decorator correcto
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_function()
    assert result is True

# Opción 3: Verificar pytest.ini
# [tool.pytest.ini_options]
# asyncio_mode = "auto"
```

---

### Coverage incorrecto o no se genera

**Síntoma**: `pytest --cov` no muestra cobertura

**Solución**:
```bash
# Reinstalar pytest-cov
pip uninstall pytest-cov
pip install pytest-cov

# Ejecutar con paths explícitos
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Verificar que src/ está en PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Ver reporte HTML
open htmlcov/index.html
```

---

### Black / flake8 conflictos

**Síntoma**: Black formatea código que flake8 rechaza

**Solución**:
```bash
# Configurar flake8 para ser compatible con Black
nano setup.cfg

[flake8]
max-line-length = 100
extend-ignore = E203, E266, E501, W503
exclude = .git,__pycache__,docs,old,build,dist

# O en pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

# Ejecutar en orden
black src/ tests/
flake8 src/ tests/
```

---

### mypy falla con missing type stubs

**Síntoma**: `error: Skipping analyzing 'aiohttp': module is installed, but missing library stubs`

**Solución**:
```bash
# Instalar stubs para librerías comunes
pip install types-redis types-aiohttp types-requests

# O ignorar warnings para librerías externas
nano pyproject.toml

[tool.mypy]
ignore_missing_imports = true  # Temporal, no ideal

# Mejor: agregar stubs específicos
[[tool.mypy.overrides]]
module = "aiohttp.*"
ignore_missing_imports = true
```

---

## Problemas de Docker

### Docker Compose no encuentra .env

**Síntoma**: Variables de entorno no se cargan

**Solución**:
```bash
# Verificar que .env existe en el directorio raíz
ls -la .env

# Si no existe, crearlo desde template
cp .env.example .env
nano .env  # Editar valores

# Verificar que docker-compose.yml lo referencia
grep "env_file" docker-compose.yml
# Debe tener: env_file: .env

# Forzar recreación de containers
docker-compose down
docker-compose up -d --force-recreate
```

---

### PostgreSQL no acepta conexiones

**Síntoma**: `psycopg2.OperationalError: could not connect to server`

**Solución**:
```bash
# Verificar que container está running
docker ps | grep postgres

# Ver logs
docker logs postgres

# Verificar puerto
docker port postgres
# Debe mostrar: 5432/tcp -> 0.0.0.0:5432

# Test conexión
docker exec -it postgres psql -U charo_user -d charo_db
# Debe entrar al shell de PostgreSQL

# Si falla, recrear volumen
docker-compose down -v
docker-compose up -d postgres
```

---

### Redis connection refused

**Síntoma**: `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`

**Solución**:
```bash
# Verificar container
docker ps | grep redis
docker logs redis

# Test conexión
docker exec -it redis redis-cli ping
# Debe responder: PONG

# Verificar que el host es correcto desde otro container
# Usar nombre del servicio, no localhost
# ❌ MAL: redis_client = redis.Redis(host="localhost")
# ✅ BIEN: redis_client = redis.Redis(host="redis")
```

---

## Problemas de Rendimiento

### Latencia total > 5 segundos

**Síntoma**: Comandos de voz tardan mucho en ejecutarse

**Solución**:
```bash
# 1. Medir cada etapa con benchmark
python tools/benchmark.py

# 2. Identificar el cuello de botella
# Etapas típicas:
# - Wake word: ~50ms (normal)
# - Audio capture: ~1.2s (normal)
# - STT RunPod: ~800ms (normal) / >2s (problema)
# - Intent recognition: ~100ms (normal)
# - HA API call: ~200ms (normal)
# - TTS: ~300ms (normal)

# 3. Si STT es lento:
# - Verificar cache hit rate (debe ser >30%)
# - Implementar fallback local con whisper.cpp

# 4. Si Intent es lento:
# - Mover más comandos a pattern matching local
# - Reducir llamadas a LLM

# 5. Si HA API es lento:
# - Verificar latencia de red entre Pi5 y HA
# - Revisar si HA está sobrecargado
```

---

### Uso de CPU muy alto en Pi5

**Síntoma**: `htop` muestra CPU al 100%

**Solución**:
```bash
# Identificar proceso culpable
htop
# O
docker stats

# Si es PostgreSQL:
# Reducir workers
nano ~/homeassistant/config/configuration.yaml
# recorder:
#   db_max_retries: 3
#   db_retry_wait: 3

# Si es charo-core:
# Reducir workers de uvicorn
nano deployment/docker/pi5-compose.yml
# command: uvicorn main:app --host 0.0.0.0 --port 8080 --workers 2

# Si es Redis:
# Configurar maxmemory
docker exec -it redis redis-cli CONFIG SET maxmemory 256mb
docker exec -it redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

### Memoria RAM se agota

**Síntoma**: Sistema swap muy activo, servicios crashean

**Solución**:
```bash
# Ver uso de memoria
free -h
docker stats

# Limitar memoria de containers
nano docker-compose.yml

services:
  postgres:
    mem_limit: 512m
  redis:
    mem_limit: 256m
  charo-core:
    mem_limit: 1g

# Aumentar swap (temporal)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=4096
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## Diagnostic Scripts

### Script completo de diagnóstico

Crear `tools/diagnose.sh`:

```bash
#!/bin/bash

echo "=== CHARO DIAGNOSTICS ==="
echo

echo "1. Python Version:"
python --version

echo -e "\n2. Pis Connectivity:"
ping -c 1 192.168.1.100 && echo "Pi4: OK" || echo "Pi4: FAIL"
ping -c 1 192.168.1.101 && echo "Pi5: OK" || echo "Pi5: FAIL"

echo -e "\n3. Docker Services:"
docker ps --format "table {{.Names}}\t{{.Status}}"

echo -e "\n4. Audio Devices:"
arecord -l 2>/dev/null || echo "No recording devices"
pactl list short sinks | grep -i bluetooth

echo -e "\n5. Network Ports:"
sudo netstat -tulpn | grep -E "8080|8082|5432|6379|8123"

echo -e "\n6. Disk Space:"
df -h | grep -E "/$|/home"

echo -e "\n7. Memory Usage:"
free -h

echo -e "\n8. CPU Load:"
uptime

echo -e "\n=== END DIAGNOSTICS ==="
```

```bash
chmod +x tools/diagnose.sh
./tools/diagnose.sh
```

---

## Recursos Adicionales

- [Home Assistant Troubleshooting](https://www.home-assistant.io/docs/configuration/troubleshooting/)
- [RunPod Documentation](https://docs.runpod.io/)
- [Docker Debugging](https://docs.docker.com/config/containers/logging/)
- [pytest Documentation](https://docs.pytest.org/)
- [GitHub Issues](https://github.com/tu-usuario/WayneHomeLab/issues)

---

**Si el problema persiste**: Abrir un issue en GitHub con:
1. Descripción del problema
2. Logs relevantes
3. Output de `./tools/diagnose.sh`
4. Pasos para reproducir

*Última actualización: Enero 2025*
