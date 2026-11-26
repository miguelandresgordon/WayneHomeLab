"""Groq Whisper prompt (vocabulary bias) is versioned and applied via HA options flow."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STT_DIR = REPO_ROOT / "infrastructure" / "voice" / "stt"
PROMPT = REPO_ROOT / "home-assistant" / "voice" / "groq_stt_prompt.txt"
sys.path.insert(0, str(STT_DIR))


def _prompt() -> str:
    return PROMPT.read_text(encoding="utf-8").strip()


def test_prompt_file_exists_and_is_single_paragraph() -> None:
    text = _prompt()
    assert text
    assert "\n" not in text


def test_prompt_is_within_whisper_prompt_budget() -> None:
    # Whisper keeps only the last 224 prompt tokens; ~1.6 tokens/word in Spanish.
    assert len(_prompt().split()) * 1.6 <= 224


def test_prompt_models_full_radio_commands_with_leading_verb() -> None:
    text = _prompt()
    # Written as example commands so Whisper keeps the leading "Pon".
    for needle in ("Pon la Cadena SER", "Para la radio", "Radio 3", "RadioVoz", "Filispim", "Almenara"):
        assert needle in text, needle


def test_prompt_keeps_core_device_vocabulary() -> None:
    text = _prompt().lower()
    for word in ("lámpara", "tele", "radio", "música", "siguiente", "modo reunión"):
        assert word in text, word


def test_options_payload_preserves_model_and_temperature() -> None:
    import apply_groq_prompt

    current = {"model": "whisper-large-v3", "prompt": "viejo", "temperature": 0.0}
    payload = apply_groq_prompt.build_options(current, "nuevo")
    assert payload == {"model": "whisper-large-v3", "prompt": "nuevo", "temperature": 0.0}


def test_options_payload_never_switches_to_turbo() -> None:
    import apply_groq_prompt

    payload = apply_groq_prompt.build_options({"model": "whisper-large-v3-turbo", "temperature": 0.0}, "p")
    assert payload["model"] == "whisper-large-v3"
