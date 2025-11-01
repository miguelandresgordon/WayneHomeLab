# API Reference - Proyecto Charo

Documentación completa de las APIs internas y endpoints del proyecto.

## Índice

1. [Voice Controller API](#voice-controller-api)
2. [Home Assistant Client](#home-assistant-client)
3. [Intent Recognition Engine](#intent-recognition-engine)
4. [Cache Manager](#cache-manager)
5. [RunPod Gateway](#runpod-gateway)
6. [Audio Service WebSocket](#audio-service-websocket)
7. [Data Models](#data-models)

---

## Voice Controller API

### Endpoint Principal

**Base URL**: `http://192.168.1.101:8080`

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0-alpha",
  "services": {
    "postgres": "up",
    "redis": "up",
    "home_assistant": "up",
    "runpod": "up"
  },
  "latencies": {
    "p50": 2.1,
    "p95": 3.2,
    "p99": 4.5
  }
}
```

---

### Process Voice Command

```http
POST /api/v1/voice/command
Content-Type: application/json
```

**Request Body**:
```json
{
  "audio_data": "base64_encoded_audio",
  "sample_rate": 16000,
  "channels": 1,
  "format": "wav"
}
```

**Response**:
```json
{
  "success": true,
  "transcription": "enciende la luz del salón",
  "intent": "control_light",
  "entities": {
    "device": "light.xiaomi_bulb",
    "action": "turn_on",
    "location": "salón"
  },
  "executed": true,
  "response_text": "Vale, enciendo la luz del salón",
  "latency_ms": 2500,
  "breakdown": {
    "stt": 800,
    "intent": 100,
    "execution": 200,
    "tts": 300
  }
}
```

**Errors**:
```json
{
  "success": false,
  "error": "STT_TIMEOUT",
  "message": "RunPod STT service timeout",
  "retry_after": 5
}
```

---

### Get Metrics

```http
GET /api/v1/metrics
```

**Response**:
```json
{
  "commands_total": 1234,
  "commands_today": 45,
  "success_rate": 0.95,
  "avg_latency_ms": 2300,
  "cache_hit_rate": 0.35,
  "top_commands": [
    {"command": "enciende la luz", "count": 234},
    {"command": "apaga la luz", "count": 189},
    {"command": "qué hora es", "count": 156}
  ]
}
```

---

## Home Assistant Client

Clase: `HomeAssistantClient`

### Initialization

```python
from charo_core.ha_client import HomeAssistantClient

client = HomeAssistantClient(
    host="192.168.1.101",
    token="eyJ0eXAiOiJKV1QiLCJhbGc..."
)
```

### Methods

#### control_light()

Control luces de Home Assistant.

```python
async def control_light(
    entity_id: str,
    action: str,
    brightness: Optional[int] = None,
    color: Optional[tuple[int, int, int]] = None
) -> dict[str, Any]
```

**Parameters**:
- `entity_id`: ID de la entidad (ej: `light.xiaomi_bulb`)
- `action`: Acción (`on`, `off`, `toggle`)
- `brightness`: Brillo 0-255 (opcional)
- `color`: RGB tuple (opcional)

**Returns**:
```python
{
    "success": True,
    "entity_id": "light.xiaomi_bulb",
    "state": "on",
    "attributes": {
        "brightness": 255,
        "rgb_color": [255, 255, 255]
    }
}
```

**Example**:
```python
# Encender luz al 50%
result = await client.control_light(
    "light.xiaomi_bulb",
    "on",
    brightness=127
)

# Encender luz en rojo
result = await client.control_light(
    "light.xiaomi_bulb",
    "on",
    color=(255, 0, 0)
)
```

---

#### control_tv()

Control TV Sony.

```python
async def control_tv(
    action: str,
    source: Optional[str] = None,
    volume: Optional[int] = None
) -> dict[str, Any]
```

**Parameters**:
- `action`: Acción (`turn_on`, `turn_off`, `select_source`, `volume_up`, `volume_down`)
- `source`: Fuente de video (ej: `Netflix`, `HDMI 1`)
- `volume`: Nivel de volumen 0-100

**Returns**:
```python
{
    "success": True,
    "entity_id": "media_player.tv_sony",
    "state": "on",
    "attributes": {
        "source": "Netflix",
        "volume_level": 0.5
    }
}
```

**Example**:
```python
# Encender TV en Netflix
result = await client.control_tv("turn_on", source="Netflix")

# Subir volumen
result = await client.control_tv("volume_up")
```

---

#### get_device_state()

Obtener estado actual de un dispositivo.

```python
async def get_device_state(entity_id: str) -> dict[str, Any]
```

**Example**:
```python
state = await client.get_device_state("light.xiaomi_bulb")
# {
#     "entity_id": "light.xiaomi_bulb",
#     "state": "on",
#     "attributes": {...},
#     "last_changed": "2025-01-15T10:30:00"
# }
```

---

#### call_service()

Llamada genérica a cualquier servicio de HA.

```python
async def call_service(
    domain: str,
    service: str,
    data: dict[str, Any]
) -> dict[str, Any]
```

**Example**:
```python
# Crear notificación
await client.call_service(
    "notify",
    "persistent_notification",
    {
        "message": "Luz encendida",
        "title": "Charo"
    }
)
```

---

## Intent Recognition Engine

Clase: `IntentRecognitionEngine`

### Initialization

```python
from charo_core.intent_engine import IntentRecognitionEngine

engine = IntentRecognitionEngine()
await engine.initialize()
```

### Methods

#### classify_intent()

Clasificar intención de un comando de voz.

```python
async def classify_intent(text: str) -> Intent
```

**Example**:
```python
intent = await engine.classify_intent("enciende la luz del salón")

# Intent object:
# {
#     "type": "control_light",
#     "action": "turn_on",
#     "entities": {
#         "device": "light.xiaomi_bulb",
#         "location": "salón"
#     },
#     "confidence": 0.95,
#     "requires_llm": False
# }
```

---

#### extract_entities()

Extraer entidades de un texto.

```python
def extract_entities(text: str) -> dict[str, str]
```

**Example**:
```python
entities = engine.extract_entities("enciende la luz del salón al 50%")
# {
#     "device": "light",
#     "location": "salón",
#     "brightness": "50"
# }
```

---

#### query_llm()

Procesar comando complejo con LLM (RunPod).

```python
async def query_llm(text: str, context: Optional[dict] = None) -> Intent
```

**Example**:
```python
intent = await engine.query_llm(
    "pon la luz del salón del mismo color que ayer",
    context={"previous_color": [255, 100, 50]}
)
```

---

#### add_pattern()

Agregar nuevo patrón de reconocimiento.

```python
def add_pattern(
    pattern: str,
    intent_type: str,
    action: str,
    entity_extractor: Optional[Callable] = None
)
```

**Example**:
```python
engine.add_pattern(
    r"(enciende|prende) (la|las) (luz|luces?)",
    "control_light",
    "turn_on"
)
```

---

## Cache Manager

Clase: `CacheManager`

### Initialization

```python
from charo_core.cache_manager import CacheManager

cache = CacheManager(
    redis_host="redis",
    redis_port=6379,
    redis_db=0
)
await cache.connect()
```

### Methods

#### get_cached_transcription()

Obtener transcripción cacheada de audio.

```python
async def get_cached_transcription(audio_hash: str) -> Optional[str]
```

**Example**:
```python
import hashlib

audio_hash = hashlib.sha256(audio_data).hexdigest()
cached_text = await cache.get_cached_transcription(audio_hash)

if cached_text:
    print(f"Cache hit: {cached_text}")
else:
    # Procesar con STT
    text = await stt_service.transcribe(audio_data)
    await cache.store_transcription(audio_hash, text)
```

---

#### store_transcription()

Almacenar transcripción en cache.

```python
async def store_transcription(
    audio_hash: str,
    text: str,
    ttl: int = 3600
) -> bool
```

---

#### get_cached_response()

Obtener respuesta pre-generada.

```python
async def get_cached_response(command: str) -> Optional[str]
```

**Example**:
```python
response = await cache.get_cached_response("qué hora es")
if not response:
    response = generate_time_response()
    await cache.store_response("qué hora es", response, ttl=60)
```

---

#### invalidate_cache()

Invalidar cache específico o todo.

```python
async def invalidate_cache(pattern: Optional[str] = None) -> int
```

**Example**:
```python
# Invalidar todos los caches de lights
count = await cache.invalidate_cache("light:*")

# Invalidar todo
count = await cache.invalidate_cache()
```

---

## RunPod Gateway

### WhisperService

Servicio de Speech-to-Text.

```python
from runpod_gateway.whisper_service import WhisperService

whisper = WhisperService(
    api_key="your_runpod_key",
    endpoint_id="your_endpoint_id"
)
```

#### transcribe()

```python
async def transcribe(
    audio_data: bytes,
    language: str = "es",
    timeout: int = 30000
) -> str
```

**Example**:
```python
text = await whisper.transcribe(audio_data, language="es")
# "enciende la luz del salón"
```

---

### MistralLLMService

Servicio de procesamiento de lenguaje natural.

```python
from runpod_gateway.llm_service import MistralLLMService

llm = MistralLLMService(
    api_key="your_runpod_key",
    endpoint_id="your_endpoint_id"
)
```

#### query()

```python
async def query(
    prompt: str,
    context: Optional[dict] = None,
    max_tokens: int = 256,
    temperature: float = 0.7
) -> str
```

**Example**:
```python
response = await llm.query(
    "Extraer intent de: 'pon la luz igual que ayer'",
    context={"previous_states": {...}},
    temperature=0.3
)
```

---

## Audio Service WebSocket

### Connection

**URL**: `ws://192.168.1.101:8082/audio`

### Protocol

#### Client → Server (Audio Stream)

```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_audio",
  "chunk_id": 123,
  "is_final": false
}
```

#### Server → Client (TTS Response)

```json
{
  "type": "tts_audio",
  "data": "base64_encoded_audio",
  "chunk_id": 1,
  "total_chunks": 5
}
```

#### Server → Client (Status Updates)

```json
{
  "type": "status",
  "status": "processing",
  "message": "Transcribing audio..."
}
```

### Example Client (Python)

```python
import websockets
import asyncio
import base64

async def stream_audio():
    uri = "ws://192.168.1.101:8082/audio"
    async with websockets.connect(uri) as websocket:
        # Send audio chunks
        for chunk in audio_chunks:
            await websocket.send(json.dumps({
                "type": "audio_chunk",
                "data": base64.b64encode(chunk).decode(),
                "chunk_id": i,
                "is_final": (i == len(audio_chunks) - 1)
            }))

        # Receive TTS response
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            if data["type"] == "tts_audio":
                audio_chunk = base64.b64decode(data["data"])
                play_audio(audio_chunk)
            elif data["type"] == "status" and data["status"] == "complete":
                break

asyncio.run(stream_audio())
```

---

## Data Models

### Intent

```python
from pydantic import BaseModel
from typing import Optional

class Intent(BaseModel):
    type: str  # "control_light", "control_tv", "query_time", etc.
    action: str  # "turn_on", "turn_off", etc.
    entities: dict[str, str]
    confidence: float  # 0.0 - 1.0
    requires_llm: bool = False
    raw_text: Optional[str] = None
```

---

### VoiceCommand

```python
class VoiceCommand(BaseModel):
    audio_data: bytes
    sample_rate: int = 16000
    channels: int = 1
    format: str = "wav"
    timestamp: datetime
    user_id: Optional[str] = None
```

---

### CommandResponse

```python
class CommandResponse(BaseModel):
    success: bool
    transcription: str
    intent: Intent
    executed: bool
    response_text: str
    latency_ms: int
    breakdown: dict[str, int]
    error: Optional[str] = None
```

---

### DeviceState

```python
class DeviceState(BaseModel):
    entity_id: str
    state: str  # "on", "off", etc.
    attributes: dict[str, Any]
    last_changed: datetime
    last_updated: datetime
```

---

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `STT_TIMEOUT` | RunPod STT timeout | 504 |
| `LLM_ERROR` | LLM processing error | 500 |
| `HA_UNAVAILABLE` | Home Assistant no disponible | 503 |
| `INVALID_ENTITY` | Entity ID no existe en HA | 404 |
| `CACHE_ERROR` | Error de Redis | 500 |
| `INVALID_AUDIO` | Audio data inválido | 400 |
| `WAKE_WORD_TIMEOUT` | Wake word no detectado | 408 |
| `VAD_ERROR` | Voice Activity Detection error | 500 |

---

## Rate Limits

- **Voice Commands**: 60 req/min por usuario
- **Metrics Endpoint**: 10 req/min
- **Health Check**: Sin límite

---

## Authentication

### Internal Services

Usar JWT tokens para comunicación inter-servicios:

```python
import jwt

token = jwt.encode(
    {"service": "audio-service", "exp": datetime.utcnow() + timedelta(hours=1)},
    JWT_SECRET,
    algorithm="HS256"
)

headers = {"Authorization": f"Bearer {token}"}
```

---

## Versioning

API usa versionado semántico en URLs:

- Current: `/api/v1/...`
- Beta features: `/api/v2-beta/...`

Deprecated endpoints retornan header:
```
X-API-Deprecated: true
X-API-Sunset: 2025-12-31
```

---

## SDKs

### Python Client

```python
from charo_client import CharoClient

client = CharoClient(
    base_url="http://192.168.1.101:8080",
    api_key="optional"
)

# Process command
result = await client.process_voice_command(audio_data)

# Get metrics
metrics = await client.get_metrics()
```

### JavaScript Client (Future)

```javascript
import { CharoClient } from '@charo/client';

const client = new CharoClient({
  baseUrl: 'http://192.168.1.101:8080'
});

const result = await client.processVoiceCommand(audioData);
```

---

## Examples

### Complete Flow Example

```python
import asyncio
from charo_core import VoiceController, HomeAssistantClient, CacheManager

async def main():
    # Initialize services
    ha_client = HomeAssistantClient("192.168.1.101", HA_TOKEN)
    cache = CacheManager("redis", 6379)
    await cache.connect()

    controller = VoiceController(ha_client, cache)

    # Process audio
    with open("test_audio.wav", "rb") as f:
        audio_data = f.read()

    result = await controller.process_command(audio_data)

    print(f"Transcription: {result.transcription}")
    print(f"Intent: {result.intent.type}")
    print(f"Executed: {result.executed}")
    print(f"Response: {result.response_text}")
    print(f"Latency: {result.latency_ms}ms")

asyncio.run(main())
```

---

## Testing

### Mock Services

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_ha_client():
    client = AsyncMock(spec=HomeAssistantClient)
    client.control_light.return_value = {"success": True, "state": "on"}
    return client

async def test_voice_controller(mock_ha_client):
    controller = VoiceController(mock_ha_client, cache=None)
    result = await controller.process_command(test_audio)
    assert result.success is True
    mock_ha_client.control_light.assert_called_once()
```

---

## Changelog

### v1.0.0-alpha (Current)
- Initial release
- Basic voice command processing
- Home Assistant integration
- RunPod STT/LLM
- Redis caching

### Roadmap v1.1.0
- Multi-user support
- Context-aware responses
- Webhook integrations
- REST webhooks for external services

---

## Support

- **Documentation**: [README.md](../README.md)
- **Issues**: [GitHub Issues](https://github.com/tu-usuario/WayneHomeLab/issues)
- **Examples**: [examples/](../examples/)

---

*Última actualización: Enero 2025*
