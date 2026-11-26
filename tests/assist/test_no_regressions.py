"""Custom sentences must not steal built-in HA commands we use every day.

HA ranks custom sentences above built-ins even with wildcards, so a greedy
custom pattern ("pon {x} de {y}") would hijack light commands. Phrases taken
from real Groq transcripts (F0 baseline).
"""

from __future__ import annotations

import pytest

LIGHT_BUILTINS = [
    "Pon la lámpara al mínimo.",
    "Pon el brillo de la lámpara al 50%.",
    "Pon la lámpara al máximo.",
    "Pon la lámpara al 50%.",
    "Pon el brillo de la lámpara al máximo.",
]


@pytest.mark.parametrize("text", LIGHT_BUILTINS)
def test_light_brightness_stays_builtin(ha_match, text) -> None:
    assert ha_match(text)[0] == "HassLightSet"


@pytest.mark.parametrize(
    "text,intent",
    [
        ("enciende la lámpara", "EnciendeLaLampara"),
        ("apaga la lámpara", "ApagaLaLampara"),
        ("apaga la tele", "ApagaLaTele"),
        ("enciende la tele", "EnciendeLaTele"),
        ("Pon el HDMI 3 en la tele.", "CambiaEntradaTele"),
        ("Para la radio.", "ParaRadioFavorita"),
        ("Pon la SER.", "PonRadioFavorita"),
    ],
)
def test_daily_commands_keep_their_intent(ha_match, text, intent) -> None:
    assert ha_match(text)[0] == intent
