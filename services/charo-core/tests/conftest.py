"""Pytest configuration and shared fixtures for charo-core tests."""

import pytest
from typing import AsyncGenerator


@pytest.fixture
def ha_test_host() -> str:
    """Home Assistant test host."""
    return "192.168.1.101"


@pytest.fixture
def ha_test_token() -> str:
    """Home Assistant test token."""
    return "test_token_12345"


@pytest.fixture
def valid_entity_id() -> str:
    """Valid Home Assistant entity ID for testing."""
    return "light.xiaomi_bulb"


@pytest.fixture
def invalid_entity_id() -> str:
    """Invalid Home Assistant entity ID for testing."""
    return "invalid.entity"
