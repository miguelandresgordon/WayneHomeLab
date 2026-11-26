"""Radio route: Music Assistant (Sendspin) first, ESPHome player as fallback.

Measured 2026-11-26 (radio_probe.py, SER): ESPHome player via HA ffmpeg proxy
starts in ~1 s but the Satellite1 drops the proxy stream after 97-173 s and
never resumes; via Music Assistant it starts in ~6 s and does not cut.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = yaml.safe_load((REPO / "home-assistant" / "includes" / "scripts.yaml").read_text(encoding="utf-8"))
MA = "media_player.satellite1"
ESPHOME = "media_player.satellite1_c7ffe4_media_player"


def _blob(name: str) -> str:
    return yaml.dump(SCRIPTS[name], allow_unicode=True)


def test_radio_helper_script_exists_with_ma_first_and_esphome_fallback() -> None:
    s = SCRIPTS["reproducir_stream_satellite"]
    blob = yaml.dump(s)
    assert MA in blob and ESPHOME in blob
    # MA is chosen when available
    assert "unavailable" in blob
    assert blob.index(MA) < blob.rindex(ESPHOME)


def test_favourites_and_radio_browser_use_the_helper() -> None:
    for name in ("poner_radio", "poner_radio_browser"):
        blob = _blob(name)
        assert "script.reproducir_stream_satellite" in blob, name
        assert "media_player.play_media" not in blob, f"{name} must not bypass the helper"


def test_stop_stops_both_players() -> None:
    blob = _blob("parar_radio")
    assert MA in blob and ESPHOME in blob
