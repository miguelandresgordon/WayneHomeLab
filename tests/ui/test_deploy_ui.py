"""deploy_ha_voice_config.sh also ships UI assets (themes, www/wayne, dashboards)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEPLOY = REPO / "infrastructure" / "voice" / "wake-word" / "deploy_ha_voice_config.sh"


def test_deploy_copies_themes_www_and_dashboards() -> None:
    text = DEPLOY.read_text(encoding="utf-8")
    assert "home-assistant/themes" in text
    assert "www/wayne" in text
    assert "home-assistant/dashboards" in text


def test_deploy_takes_a_backup_first() -> None:
    text = DEPLOY.read_text(encoding="utf-8")
    assert "ha_backup_config.sh" in text
    assert text.index("ha_backup_config.sh") < text.index("scp ")
