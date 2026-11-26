"""Radio phrases (custom_sentences/es/radio.yaml) incl. real Groq STT variants.

Real failures come from /share/assist_pipeline WAVs re-transcribed with the
production STT (F0 baseline, 2026-11-26): the leading "Pon" is often clipped
right after the wake word -> "Con la SER", "Hola SER", "O la cadena SER"...
"""

from __future__ import annotations

import pytest

STATIONS = {
    "ser": ["ser", "la ser", "cadena ser", "la cadena ser", "radio madrid", "cadena cero", "ser madrid"],
    "radiovoz": ["radiovoz", "radio voz", "radiovoz lugo", "radio voz lugo"],
    "filispim": ["filispim", "filispín", "radio filispim"],
    "almenara": ["almenara", "radio almenara"],
    "radio3": ["radio 3", "radio tres", "rne", "radio 3 de rne"],
    "roncudo": ["roncudo", "radio roncudo"],
}

VERBS = [
    "pon",
    "ponme",
    "ponla",
    "pon la radio",
    "sintoniza",
    "sintonízame",
    "quiero oír",
    "quiero escuchar",
    "reproduce",
    "me pones",
    "puedes poner",
]


@pytest.mark.parametrize("key,names", sorted(STATIONS.items()))
@pytest.mark.parametrize("verb", VERBS)
def test_every_station_with_every_verb(match, key, names, verb) -> None:
    for name in names:
        text = f"{verb} {name}"
        assert match(text) == ("PonRadioFavorita", {"emisora": key}), text


# Exact strings returned by Groq whisper-large-v3 for real "pon la SER" requests.
REAL_STT_SER = [
    "Pon la cadena SER.",
    "Pon la SER.",
    "Con la SER.",
    "Con la cadena SER.",
    "O la cadena SER.",
    "Hola SER.",
    "Hola, Cadena SER.",
    "Hola, Cadena Cero.",
    "¡Von la SER!",
    "Ponla SER.",
    "Con la cadena SER en la radio.",
    "Pon la cadena SER en la radio.",
    "ponme la cadena ser",
    "sintoniza la ser",
    "quiero oír la ser",
    "la ser",
    "la cadena ser",
]


@pytest.mark.parametrize("text", REAL_STT_SER)
def test_real_stt_variants_put_the_ser(match, text) -> None:
    assert match(text) == ("PonRadioFavorita", {"emisora": "ser"})


@pytest.mark.parametrize("text", ["Hola Radio.", "pon la radio", "ponme la radio", "con la radio", "enciende la radio"])
def test_bare_radio_defaults_to_ser(match, text) -> None:
    assert match(text) == ("PonRadioFavorita", {"emisora": "ser"})


@pytest.mark.parametrize("text", ["Pon radio 3", "pon la radio 3", "Pon Radio 3."])
def test_radio_3_is_a_favourite_not_a_radio_browser_search(match, text) -> None:
    assert match(text) == ("PonRadioFavorita", {"emisora": "radio3"})


@pytest.mark.parametrize(
    "text,query",
    [("pon la radio bbc", "bbc"), ("Pon la radio Cadena 100", "cadena 100"), ("busca la radio los 40", "los 40")],
)
def test_radio_browser_by_name_uses_wildcard(match, text, query) -> None:
    intent, slots = match(text)
    assert intent == "PonRadioBrowser"
    assert slots["consulta"].strip().lower() == query


def test_radio_browser_wildcard_list_is_defined(custom_intents) -> None:
    # Undefined {consulta} made HA answer "Unknown error" live (2026-11-26).
    assert "consulta" in custom_intents.slot_lists


@pytest.mark.parametrize(
    "text",
    ["Para la radio.", "apaga la radio", "quita la radio", "para la ser", "apaga la cadena ser", "deja de reproducir la radio", "silencio radio"],
)
def test_stop_phrases(match, text) -> None:
    assert match(text)[0] == "ParaRadioFavorita"


@pytest.mark.parametrize(
    "text",
    [
        "Pon la lámpara al mínimo.",
        "Pon el brillo de la lámpara al 50%.",
        "con la tele",
        "hola",
        "Pon el HDMI 3 en la tele.",
        "¿Qué va a ser movido?",
        "Deberíamos ser civiles.",
    ],
)
def test_non_radio_sentences_do_not_start_the_radio(match, text) -> None:
    assert match(text)[0] not in {"PonRadioFavorita", "PonRadioBrowser", "PonRadioLista", "PonRadioAleatoria"}
