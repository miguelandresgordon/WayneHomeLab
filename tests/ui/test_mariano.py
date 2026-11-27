"""Mariano dashboard + STT telemetry wiring."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
HA = REPO / "home-assistant"
DASH = HA / "dashboards" / "mariano.yaml"


def test_last_stt_text_is_wired_to_the_firmware_event() -> None:
    pkg = yaml.safe_load((HA / "packages" / "voz_telemetria.yaml").read_text(encoding="utf-8"))
    a = pkg["automation"][0]
    blob = yaml.dump(a, allow_unicode=True)
    assert "esphome.satellite1_stt_end" in blob
    assert "input_text.last_stt_text" in blob
    assert "[:255]" in blob or "truncate(255" in blob  # input_text max


def test_dashboard_shows_what_was_asked() -> None:
    b = DASH.read_text(encoding="utf-8")
    for needle in (
        "switch.satellite1_c7ffe4_wake_word_activo",
        "select.satellite1_c7ffe4_wake_word_sensitivity",
        "switch.satellite1_c7ffe4_mute_microphones",
        "input_text.last_stt_text",
        "input_text.current_speaker",
        "sensor.satellite1_c7ffe4_wi_fi_signal_strength",
        "media_player.satellite1",
        "input_boolean.modo_reunion",
        "timer.modo_reunion",
        "sensor.satellite1_c7ffe4_mic_level",
        "latencias",
        "chuleta",
    ):
        assert needle.lower() in b.lower(), needle


def test_cheat_sheet_matches_real_sentences() -> None:
    b = DASH.read_text(encoding="utf-8")
    for phrase in ("pon la SER", "para la radio", "activa el modo reunión", "pon mi playlist", "siguiente", "enciende la lámpara"):
        assert phrase.lower() in b.lower(), phrase
