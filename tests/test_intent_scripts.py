"""Every custom intent has an intent_script handler (and vice versa)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
HA = REPO / "home-assistant"
BUILTIN_OVERRIDES: set[str] = set()


def _custom_intents() -> set[str]:
    names: set[str] = set()
    for p in (HA / "custom_sentences" / "es").glob("*.yaml"):
        names |= set((yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("intents", {}))
    return names


def _scripts() -> dict:
    return yaml.safe_load((HA / "includes" / "intent_scripts.yaml").read_text(encoding="utf-8"))


def test_every_custom_intent_has_a_handler() -> None:
    missing = _custom_intents() - set(_scripts())
    assert not missing, f"custom intents without intent_script: {sorted(missing)}"


def test_no_orphan_handlers() -> None:
    orphans = set(_scripts()) - _custom_intents() - BUILTIN_OVERRIDES
    assert not orphans, f"intent_script without sentences: {sorted(orphans)}"


def test_lamp_brightness_is_pinned_to_the_xiaomi_lamp() -> None:
    s = _scripts()["LamparaBrillo"]
    blob = yaml.dump(s)
    assert "light.yeelink_mono6_6409_light" in blob
    assert "brightness_pct" in blob
