"""Casa (esencial): only the daily controls, phone-friendly."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
HA = REPO / "home-assistant"
DASH = HA / "dashboards" / "casa.yaml"


def _blob() -> str:
    return DASH.read_text(encoding="utf-8")


def test_sections_view_phone_friendly() -> None:
    d = yaml.safe_load(_blob())
    assert len(d["views"]) == 1
    v = d["views"][0]
    assert v["type"] == "sections" and v.get("max_columns", 4) <= 3
    assert len(v["sections"]) >= 5


def test_daily_controls_present() -> None:
    b = _blob()
    for needle in (
        "light.yeelink_mono6_6409_light",
        "media_player.tv_ga_2",
        "media_player.satellite1",  # ahora suena (Music Assistant)
        "media_player.satellite1_c7ffe4_media_player",  # volumen del altavoz
        "script.poner_radio",
        "script.parar_radio",
        "script.musica_buscar_y_poner",
        "input_boolean.modo_reunion",
        "script.apagar_todo",
    ):
        assert needle in b, needle
    for station in ("ser", "radio3", "radiovoz", "filispim", "almenara"):
        assert f"emisora: {station}" in b, station


def test_nothing_out_of_scope() -> None:
    b = _blob().lower()
    for banned in ("job", "weather", "aemet", "gemini", "speaker", "mic_level"):
        assert banned not in b, banned


def test_apagar_todo_script() -> None:
    s = yaml.safe_load((HA / "includes" / "scripts.yaml").read_text(encoding="utf-8"))["apagar_todo"]
    blob = yaml.dump(s)
    for e in ("light.yeelink_mono6_6409_light", "media_player.tv_ga_2", "media_player.satellite1"):
        assert e in blob, e
    assert "continue_on_error: true" in blob
