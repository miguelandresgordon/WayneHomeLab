"""Lamp/TV phrases with clipped verbs seen in real Groq transcripts (F0).

HA falls back to fuzzy matching when nothing matches strictly; after adding
"con" as a radio verb, "Con la lámpara al 50%" fuzzy-matched PonRadioFavorita
live (2026-11-26). Strict custom sentences always beat fuzzy.
"""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "text,brillo",
    [
        ("Con la lámpara al 50%.", 50),
        ("Con la lámpara el 50%.", 50),
        ("con la lámpara al 100%", 100),
        ("Con el brillo de la lámpara al máximo.", 100),
        ("con la lámpara al mínimo", 1),
        ("pon la lámpara al 30 por ciento", 30),
        ("ponme la lámpara al máximo", 100),
    ],
)
def test_lamp_brightness_with_clipped_verbs(match, text, brillo) -> None:
    intent, slots = match(text)
    assert intent == "LamparaBrillo"
    assert int(slots["brillo"]) == brillo


@pytest.mark.parametrize("text", ["Entiende la lámpara.", "Conciende la lámpara.", "enciende la lámpara"])
def test_lamp_on_clipped(match, text) -> None:
    assert match(text)[0] == "EnciendeLaLampara"


@pytest.mark.parametrize("text", ["Apagada la lámpara.", "apágala lámpara", "apaga la lámpara"])
def test_lamp_off_clipped(match, text) -> None:
    assert match(text)[0] == "ApagaLaLampara"


@pytest.mark.parametrize("text", ["Aparar la tele.", "apágame la tele", "apaga la tele"])
def test_tv_off_clipped(match, text) -> None:
    assert match(text)[0] == "ApagaLaTele"
