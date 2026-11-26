"""create_ha_user.py: non-admin HA user + person, random temp password never logged."""

from __future__ import annotations

import string
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "infrastructure" / "ha"))

import create_ha_user as c  # noqa: E402


def test_password_is_random_long_and_mixed() -> None:
    a, b = c.generate_password(), c.generate_password()
    assert a != b
    assert len(a) >= 20
    assert any(ch in string.ascii_lowercase for ch in a)
    assert any(ch in string.ascii_uppercase for ch in a)
    assert any(ch in string.digits for ch in a)


def test_user_payload_is_not_admin() -> None:
    p = c.user_payload("Alicia")
    assert p["type"] == "config/auth/create"
    assert p["group_ids"] == ["system-users"]
    assert "system-admin" not in str(p)


def test_credentials_payload_uses_lowercase_username() -> None:
    p = c.credentials_payload("uid123", "Alicia", "pw")
    assert p == {"type": "config/auth_provider/homeassistant/create", "user_id": "uid123", "username": "alicia", "password": "pw"}


def test_person_payload_links_user() -> None:
    p = c.person_payload("Alicia", "uid123")
    assert p["type"] == "person/create" and p["user_id"] == "uid123" and p["name"] == "Alicia"


def test_password_goes_to_private_file_not_stdout(tmp_path, capsys) -> None:
    out = tmp_path / "pw"
    c.write_secret(out, "s3cret")
    assert out.read_text() == "s3cret\n"
    assert (out.stat().st_mode & 0o777) == 0o600
    assert "s3cret" not in capsys.readouterr().out
