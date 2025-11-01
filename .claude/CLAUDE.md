# Guía de Desarrollo - Proyecto Charo

## Metodología: Test-Driven Development (TDD) Estricto

### Flujo TDD Obligatorio

1. **RED**: Escribir tests que fallan
   - Define entrada/salida esperada
   - NO uses mocks ni simulaciones
   - Ejecuta el test y CONFIRMA que falla
   - NO escribas código de implementación en esta fase

2. **Commit Tests**: Cuando estés satisfecho con los tests
   ```bash
   git add tests/
   git commit -m "test: add tests for [feature]"
   ```

3. **GREEN**: Implementar código que pase los tests
   - Sin modificar los tests existentes
   - Código mínimo para pasar los tests
   - Ejecuta tests continuamente

4. **REFACTOR**: Mejorar código manteniendo tests verdes
   - Limpieza de código
   - Optimizaciones
   - Tests deben seguir pasando

5. **Commit Implementation**:
   ```bash
   git add src/
   git commit -m "feat: implement [feature]"
   ```

---

## Estructura del Proyecto

### Servicios Principales

```
services/
├── charo-core/          # Pi5 - Voice Controller, Intent Engine, HA Client
├── audio-service/       # Pi4 - Wake Word, VAD, Audio Capture
├── runpod-gateway/      # RunPod Client (Whisper, Mistral)
└── home-assistant/      # HA Configuration
```

### Archivos Clave

| Archivo | Propósito | Test Location |
|---------|-----------|---------------|
| `services/charo-core/src/ha_client.py` | Cliente Home Assistant API | `services/charo-core/tests/test_ha_client.py` |
| `services/charo-core/src/intent_engine.py` | Reconocimiento de intenciones | `services/charo-core/tests/test_intent_engine.py` |
| `services/charo-core/src/cache_manager.py` | Gestor de caché Redis | `services/charo-core/tests/test_cache_manager.py` |
| `services/charo-core/src/voice_controller.py` | Orquestador principal | `services/charo-core/tests/test_voice_controller.py` |
| `services/audio-service/src/wake_word.py` | Detector wake word | `services/audio-service/tests/test_wake_word.py` |
| `services/audio-service/src/vad.py` | Voice Activity Detection | `services/audio-service/tests/test_vad.py` |

---

## Comandos Bash Comunes

### Desarrollo Local

```bash
# Setup inicial
cd services/charo-core
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Ejecutar tests (siempre antes de commit)
pytest tests/ -v                    # Tests básicos
pytest tests/ -v --cov=src         # Con cobertura
pytest tests/ -v -k test_nombre    # Test específico
pytest tests/ -x                   # Parar en primer fallo
pytest tests/ --pdb                # Debugger en fallo

# Linting (ejecutar antes de commit)
black src/ tests/                  # Formateo
flake8 src/ tests/                 # Linter
mypy src/                          # Type checking

# Watch mode (desarrollo activo)
ptw -- tests/                      # pytest-watch

# Docker
docker-compose up -d postgres redis
docker-compose logs -f charo-core
docker-compose down
```

### Git Workflow

```bash
# Crear rama para feature
git checkout -b feat/intent-recognition

# TDD cycle
git add tests/test_intent_engine.py
git commit -m "test: add intent recognition tests"
# Implementar...
git add src/intent_engine.py
git commit -m "feat: implement intent recognition"

# Antes de push
pytest tests/ -v --cov=src
black src/ tests/
flake8 src/ tests/
mypy src/

git push origin feat/intent-recognition
```

---

## Directrices de Estilo de Código

### Python Style Guide

```python
# Formato: Black (line length 100)
# Imports: isort compatible
# Type hints: Siempre (mypy strict)

# Ejemplo estructura de clase
class HomeAssistantClient:
    """Cliente para interactuar con Home Assistant API.

    Args:
        host: IP o hostname de Home Assistant
        token: Long-lived access token

    Raises:
        ValueError: Si host o token son vacíos
        ConnectionError: Si no puede conectar a HA
    """

    def __init__(self, host: str, token: str) -> None:
        if not host or not token:
            raise ValueError("Host and token are required")
        self.base_url = f"http://{host}:8123/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def control_light(
        self,
        entity_id: str,
        action: str,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Control luces de Home Assistant.

        Args:
            entity_id: ID de la entidad (ej: light.xiaomi_bulb)
            action: Acción a ejecutar (on, off, toggle)
            **kwargs: Parámetros adicionales (brightness, color, etc)

        Returns:
            Respuesta de HA API

        Raises:
            APIError: Si la petición falla
        """
        service = f"light.turn_{action}"
        return await self.call_service("light", service, {"entity_id": entity_id, **kwargs})


# Ejemplo estructura de test
class TestHomeAssistantClient:
    """Tests para HomeAssistantClient."""

    def test_control_light_turn_on_success(self):
        """Debe encender luz correctamente cuando HA responde OK."""
        # ARRANGE
        client = HomeAssistantClient("192.168.1.101", "test-token")

        # ACT
        result = await client.control_light("light.xiaomi_bulb", "on")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == "light.xiaomi_bulb"
        assert result["state"] == "on"

    def test_control_light_invalid_entity_raises_error(self):
        """Debe lanzar error cuando entity_id no existe."""
        # ARRANGE
        client = HomeAssistantClient("192.168.1.101", "test-token")

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Invalid entity"):
            await client.control_light("invalid.entity", "on")
```

### Convenciones de Naming

```python
# Clases: PascalCase
class IntentRecognitionEngine: ...

# Funciones/métodos: snake_case
def extract_entities(text: str) -> list[str]: ...

# Constantes: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_MS = 5000

# Variables privadas: _underscore
class Config:
    def __init__(self):
        self._api_key = os.getenv("API_KEY")

# Tests: test_[function]_[scenario]_[expected]
def test_extract_entities_from_command_returns_list(): ...
def test_extract_entities_empty_string_returns_empty_list(): ...
```

---

## Configuración del Entorno

### Python Version Management

```bash
# Usar pyenv para gestionar versiones
pyenv install 3.11.7
pyenv local 3.11.7

# Verificar versión
python --version  # Debe ser >= 3.11
```

### Dependencias Principales

```txt
# services/charo-core/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.25.0
pydantic==2.5.0
aiohttp==3.9.1
redis==5.0.1
asyncpg==0.29.0
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-watch==4.2.0
black==23.12.1
flake8==7.0.0
mypy==1.8.0
```

```bash
# Instalar dependencias de desarrollo
pip install -r requirements.txt
pip install -e .  # Modo editable
```

### Variables de Entorno Críticas

```bash
# .env (NUNCA commitear)
HOME_ASSISTANT_TOKEN=eyJ0eXAiOiJKV1Q...
RUNPOD_API_KEY=xxxx
POSTGRES_PASSWORD=xxxx
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Librerías Clave

**aiohttp** (Cliente HTTP Async):
```python
# ClientSession para requests HTTP asíncronos
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.get('http://192.168.1.101:8123/api/') as resp:
        data = await resp.json()

# Headers y autenticación
headers = {"Authorization": f"Bearer {token}"}
async with session.post(url, json=payload, headers=headers) as resp:
    result = await resp.json()

# Manejo de errores
try:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        resp.raise_for_status()  # Lanza excepción si status >= 400
except aiohttp.ClientError as e:
    logger.error(f"HTTP error: {e}")
```

**pytest-asyncio** (Testing Async):
```python
# Decorator obligatorio para tests async
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is True

# Configurar en pyproject.toml:
# [tool.pytest.ini_options]
# asyncio_mode = "auto"
```

**pydantic** (Validación de datos):
```python
from pydantic import BaseModel, Field

class Intent(BaseModel):
    type: str = Field(..., description="Tipo de intención")
    action: str
    confidence: float = Field(ge=0.0, le=1.0)

# Validación automática
intent = Intent(type="control_light", action="on", confidence=0.95)
```

---

## Instrucciones de Prueba

### Tipos de Tests

1. **Unit Tests**: Funciones individuales con entrada/salida clara
   ```python
   def test_parse_command_light_on():
       """Input: 'enciende la luz' → Output: ('control_light', 'on')"""
       result = parse_command("enciende la luz")
       assert result == ("control_light", "on")
   ```

2. **Integration Tests**: Interacción entre componentes (sin mocks)
   ```python
   @pytest.mark.integration
   async def test_ha_client_controls_real_light():
       """Test con Home Assistant real en testcontainers."""
       client = HomeAssistantClient(HA_TEST_HOST, HA_TEST_TOKEN)
       result = await client.control_light("light.test_bulb", "on")
       assert result["success"] is True
   ```

3. **End-to-End Tests**: Pipeline completo
   ```python
   @pytest.mark.e2e
   async def test_voice_command_pipeline_end_to_end():
       """Audio input → Intent → HA → TTS output"""
       audio = load_test_audio("enciende_la_luz.wav")
       result = await process_voice_command(audio)
       assert result["action_executed"] is True
       assert result["tts_response"] == "Vale, enciendo la luz"
   ```

### Fixtures Útiles

```python
# conftest.py
import pytest
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def redis_container():
    """Redis real para tests de integración."""
    with RedisContainer() as redis:
        yield redis

@pytest.fixture
def ha_client(monkeypatch):
    """Cliente HA con configuración de test."""
    monkeypatch.setenv("HOME_ASSISTANT_HOST", "192.168.1.101")
    monkeypatch.setenv("HOME_ASSISTANT_TOKEN", "test-token")
    return HomeAssistantClient.from_env()

@pytest.fixture
def sample_audio_data():
    """Audio de prueba para tests."""
    return np.random.rand(16000).astype(np.float32)  # 1 segundo @ 16kHz
```

### Coverage Requirements

```bash
# Mínimo 80% coverage en src/
pytest tests/ --cov=src --cov-report=html --cov-fail-under=80

# Ver reporte
open htmlcov/index.html
```

---

## Etiqueta del Repositorio

### Nomenclatura de Ramas

```bash
feat/nombre-feature      # Nueva funcionalidad
fix/nombre-bug           # Corrección de bug
test/nombre-tests        # Solo tests
docs/nombre-doc          # Documentación
refactor/nombre          # Refactorización
chore/nombre             # Tareas mantenimiento
```

### Commits Semánticos

```
feat: add intent recognition engine
fix: resolve Redis connection timeout
test: add tests for cache manager
docs: update API documentation
refactor: simplify voice controller logic
chore: update dependencies
```

### Merge vs Rebase

- **Feature branches**: Rebase sobre main antes de merge
  ```bash
  git fetch origin
  git rebase origin/main
  git push --force-with-lease
  ```

- **Main branch**: Solo fast-forward merges
  ```bash
  git merge --ff-only feat/nueva-feature
  ```

- **Pull Requests**: Squash merge para features pequeños, merge commit para grandes

---

## Problemas Conocidos y Soluciones

### 1. Tests Asyncio Hanging

```python
# ❌ MAL: Test se queda colgado
async def test_my_function():
    result = await my_async_function()
    assert result is True

# ✅ BIEN: Usar decorator pytest-asyncio
@pytest.mark.asyncio
async def test_my_function():
    result = await my_async_function()
    assert result is True
```

### 2. Import Paths Incorrectos

```python
# ❌ MAL: Import relativo en tests
from ..src.ha_client import HomeAssistantClient

# ✅ BIEN: Import absoluto
from charo_core.ha_client import HomeAssistantClient

# Agregar al pyproject.toml:
[tool.pytest.ini_options]
pythonpath = ["src"]
```

### 3. Flaky Tests con Redis

```python
# ❌ MAL: Usar Redis compartido
@pytest.fixture
def redis_client():
    return redis.Redis(host="localhost", port=6379, db=0)

# ✅ BIEN: Limpiar entre tests
@pytest.fixture
def redis_client():
    client = redis.Redis(host="localhost", port=6379, db=1)
    yield client
    client.flushdb()  # Limpieza
```

### 4. Type Checking con Asyncio

```python
# Agregar a pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# Plugins necesarios
plugins = ["pydantic.mypy"]
```

---

## Checklist Pre-Commit

```bash
# Ejecutar SIEMPRE antes de commit

☐ Tests pasan: pytest tests/ -v
☐ Coverage >80%: pytest tests/ --cov=src --cov-fail-under=80
☐ Black format: black --check src/ tests/
☐ Flake8 limpio: flake8 src/ tests/
☐ Mypy limpio: mypy src/
☐ No print() statements en código
☐ No archivos .env commiteados
☐ requirements.txt actualizado si se añadieron dependencias
☐ Docstrings en funciones públicas
☐ Tests siguen patrón AAA (Arrange-Act-Assert)
```

---

## Links Útiles

- [Documentación Arquitectura](../docs/ARCHITECTURE.md)
- [Guía Setup](../docs/SETUP.md)
- [API Reference](../docs/API.md)
- [Troubleshooting](../docs/TROUBLESHOOTING.md)
- [README Completo](../README.md)

---

**Recuerda**: TDD no es opcional. Tests primero, código después.

*Última actualización: Enero 2025*
