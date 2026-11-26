"""Whisper hallucinations on silence/TV must map to a strict no-op intent.

Otherwise HA's fuzzy fallback turns them into commands: live 2026-11-26,
"Gracias por ver el video." -> PonRadioFavorita (fuzzy).
"""

from __future__ import annotations

import pytest

HALLUCINATIONS = [
    "Gracias.",
    "Gracias por ver el video.",
    "¡Gracias por ver el video! ¡Suscríbete al canal!",
    "Gracias por ver el vídeo",
    "Subtítulos realizados por la comunidad de Amara.org",
    "Suscríbete al canal",
    "Aplausos.",
    "Música.",
    "Adiós.",
]


@pytest.mark.parametrize("text", HALLUCINATIONS)
def test_hallucinations_are_ignored(match, text) -> None:
    assert match(text)[0] == "IgnorarRuido"
