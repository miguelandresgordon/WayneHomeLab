"""Tests for Home Assistant Client.

TDD Fase RED: Estos tests definen el comportamiento esperado de HomeAssistantClient.
Deben FALLAR hasta que se implemente el código en src/ha_client.py.
"""

import pytest
from ha_client import HomeAssistantClient


class TestHomeAssistantClientInit:
    """Tests para inicialización de HomeAssistantClient."""

    def test_init_with_valid_params_creates_client(self, ha_test_host: str, ha_test_token: str):
        """Debe crear cliente cuando host y token son válidos."""
        # ARRANGE & ACT
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ASSERT
        assert client is not None
        assert client.host == ha_test_host
        assert client.token == ha_test_token
        assert client.base_url == f"http://{ha_test_host}:8123/api"

    def test_init_with_empty_host_raises_value_error(self, ha_test_token: str):
        """Debe lanzar ValueError cuando host está vacío."""
        # ARRANGE
        empty_host = ""

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Host cannot be empty"):
            HomeAssistantClient(host=empty_host, token=ha_test_token)

    def test_init_with_empty_token_raises_value_error(self, ha_test_host: str):
        """Debe lanzar ValueError cuando token está vacío."""
        # ARRANGE
        empty_token = ""

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Token cannot be empty"):
            HomeAssistantClient(host=ha_test_host, token=empty_token)

    def test_init_with_none_host_raises_value_error(self, ha_test_token: str):
        """Debe lanzar ValueError cuando host es None."""
        # ACT & ASSERT
        with pytest.raises(ValueError, match="Host cannot be empty"):
            HomeAssistantClient(host=None, token=ha_test_token)

    def test_init_with_none_token_raises_value_error(self, ha_test_host: str):
        """Debe lanzar ValueError cuando token es None."""
        # ACT & ASSERT
        with pytest.raises(ValueError, match="Token cannot be empty"):
            HomeAssistantClient(host=ha_test_host, token=None)


class TestHomeAssistantClientControlLight:
    """Tests para control de luces."""

    @pytest.mark.asyncio
    async def test_control_light_turn_on_returns_success(
        self, ha_test_host: str, ha_test_token: str, valid_entity_id: str
    ):
        """Debe encender luz y retornar success=True."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.control_light(entity_id=valid_entity_id, action="on")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == valid_entity_id
        assert result["state"] == "on"

    @pytest.mark.asyncio
    async def test_control_light_turn_off_returns_success(
        self, ha_test_host: str, ha_test_token: str, valid_entity_id: str
    ):
        """Debe apagar luz y retornar success=True."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.control_light(entity_id=valid_entity_id, action="off")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == valid_entity_id
        assert result["state"] == "off"

    @pytest.mark.asyncio
    async def test_control_light_toggle_returns_success(
        self, ha_test_host: str, ha_test_token: str, valid_entity_id: str
    ):
        """Debe alternar luz y retornar success=True."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.control_light(entity_id=valid_entity_id, action="toggle")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == valid_entity_id
        # State puede ser "on" o "off" después de toggle
        assert result["state"] in ["on", "off"]

    @pytest.mark.asyncio
    async def test_control_light_with_brightness_returns_success(
        self, ha_test_host: str, ha_test_token: str, valid_entity_id: str
    ):
        """Debe encender luz con brillo específico."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)
        brightness = 127  # 50%

        # ACT
        result = await client.control_light(
            entity_id=valid_entity_id, action="on", brightness=brightness
        )

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == valid_entity_id
        assert result["state"] == "on"
        assert result.get("brightness") == brightness

    @pytest.mark.asyncio
    async def test_control_light_invalid_entity_raises_value_error(
        self, ha_test_host: str, ha_test_token: str, invalid_entity_id: str
    ):
        """Debe lanzar ValueError cuando entity_id no existe."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Invalid entity"):
            await client.control_light(entity_id=invalid_entity_id, action="on")

    @pytest.mark.asyncio
    async def test_control_light_invalid_action_raises_value_error(
        self, ha_test_host: str, ha_test_token: str, valid_entity_id: str
    ):
        """Debe lanzar ValueError cuando action es inválida."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)
        invalid_action = "explode"

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Invalid action"):
            await client.control_light(entity_id=valid_entity_id, action=invalid_action)


class TestHomeAssistantClientControlTV:
    """Tests para control de TV."""

    @pytest.mark.asyncio
    async def test_control_tv_turn_on_returns_success(
        self, ha_test_host: str, ha_test_token: str
    ):
        """Debe encender TV y retornar success=True."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.control_tv(action="turn_on")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == "media_player.tv_sony"
        assert result["state"] == "on"

    @pytest.mark.asyncio
    async def test_control_tv_turn_off_returns_success(
        self, ha_test_host: str, ha_test_token: str
    ):
        """Debe apagar TV y retornar success=True."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.control_tv(action="turn_off")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == "media_player.tv_sony"
        assert result["state"] == "off"

    @pytest.mark.asyncio
    async def test_control_tv_select_source_netflix_returns_success(
        self, ha_test_host: str, ha_test_token: str
    ):
        """Debe cambiar fuente a Netflix."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.control_tv(action="select_source", source="Netflix")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == "media_player.tv_sony"
        assert result["source"] == "Netflix"

    @pytest.mark.asyncio
    async def test_control_tv_volume_up_returns_success(
        self, ha_test_host: str, ha_test_token: str
    ):
        """Debe subir volumen de TV."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.control_tv(action="volume_up")

        # ASSERT
        assert result["success"] is True
        assert result["entity_id"] == "media_player.tv_sony"


class TestHomeAssistantClientGetDeviceState:
    """Tests para obtener estado de dispositivos."""

    @pytest.mark.asyncio
    async def test_get_device_state_returns_current_state(
        self, ha_test_host: str, ha_test_token: str, valid_entity_id: str
    ):
        """Debe retornar el estado actual del dispositivo."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        state = await client.get_device_state(entity_id=valid_entity_id)

        # ASSERT
        assert state is not None
        assert state["entity_id"] == valid_entity_id
        assert "state" in state
        assert state["state"] in ["on", "off", "unavailable"]
        assert "attributes" in state

    @pytest.mark.asyncio
    async def test_get_device_state_invalid_entity_raises_value_error(
        self, ha_test_host: str, ha_test_token: str, invalid_entity_id: str
    ):
        """Debe lanzar ValueError cuando entity_id no existe."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Entity not found"):
            await client.get_device_state(entity_id=invalid_entity_id)


class TestHomeAssistantClientCallService:
    """Tests para call_service genérico."""

    @pytest.mark.asyncio
    async def test_call_service_returns_success(
        self, ha_test_host: str, ha_test_token: str
    ):
        """Debe ejecutar servicio genérico y retornar success."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT
        result = await client.call_service(
            domain="light", service="turn_on", data={"entity_id": "light.xiaomi_bulb"}
        )

        # ASSERT
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_call_service_invalid_domain_raises_value_error(
        self, ha_test_host: str, ha_test_token: str
    ):
        """Debe lanzar ValueError cuando domain no existe."""
        # ARRANGE
        client = HomeAssistantClient(host=ha_test_host, token=ha_test_token)

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Invalid domain"):
            await client.call_service(
                domain="invalid_domain", service="some_service", data={}
            )
