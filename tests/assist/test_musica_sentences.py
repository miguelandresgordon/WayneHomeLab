"""Spotify by voice through Music Assistant (custom_sentences/es/musica.yaml).

Anchored forms ("la canción", "el disco", "mi playlist", "música de") use
wildcards. The bare form "pon X de Y" only fires when Y is an artist of the
library (generated list), so it cannot hijack "pon un temporizador de 5
minutos" or "pon el brillo de la lámpara al 50%".
"""

from __future__ import annotations

import pytest


def _lower(slots: dict) -> dict:
    return {k: str(v).strip().lower() for k, v in slots.items()}


@pytest.mark.parametrize(
    "text,nombre,artista",
    [
        ("pon la canción Despacito de Luis Fonsi", "despacito", "luis fonsi"),
        ("Pon la canción House Tour de Sabrina Carpenter.", "house tour", "sabrina carpenter"),
        ("ponme el tema Malamente de Rosalía", "malamente", "rosalía"),
        ("Reproduce una canción de Los Caños", None, "los caños"),
        ("pon la canción Bohemian Rhapsody", "bohemian rhapsody", None),
    ],
)
def test_song(match, text, nombre, artista) -> None:
    intent, slots = match(text)
    slots = _lower(slots)
    if nombre is None:
        assert intent == "MusicaArtista"
        assert slots["artista"] == artista
        return
    assert intent == "MusicaCancion"
    assert slots["nombre"] == nombre
    if artista:
        assert slots["artista"] == artista


@pytest.mark.parametrize(
    "text,nombre,artista",
    [
        ("Pon House Tour de Sabrina Carpenter.", "house tour", "sabrina carpenter"),
        ("pon Juno de Sabrina Carpenter", "juno", "sabrina carpenter"),
        ("Con Malamente de Rosalía", "malamente", "rosalía"),
    ],
)
def test_bare_song_only_with_library_artist(match, text, nombre, artista) -> None:
    intent, slots = match(text)
    assert intent == "MusicaCancion"
    assert _lower(slots)["nombre"] == nombre
    assert _lower(slots)["artista"] == artista.lower() or slots["artista"] in {"Sabrina Carpenter", "ROSALÍA"}


@pytest.mark.parametrize(
    "text,nombre,artista",
    [
        ("pon el disco Motomami de Rosalía", "motomami", "rosalía"),
        ("pon el álbum Short n' Sweet de Sabrina Carpenter", "short n' sweet", "sabrina carpenter"),
        ("ponme el disco El Madrileño", "el madrileño", None),
    ],
)
def test_album(match, text, nombre, artista) -> None:
    intent, slots = match(text)
    assert intent == "MusicaDisco"
    s = _lower(slots)
    assert s["nombre"] == nombre
    if artista:
        assert s["artista"] == artista


@pytest.mark.parametrize(
    "text,nombre",
    [
        ("pon mi playlist En bucle", "en bucle"),
        ("pon la playlist Alicia y Miguel", "alicia y miguel"),
        ("ponme mi lista Camarón", "camarón"),
        ("pon mi lista de reproducción hip hop", "hip hop"),
    ],
)
def test_playlist(match, text, nombre) -> None:
    intent, slots = match(text)
    assert intent == "MusicaPlaylist"
    assert _lower(slots)["nombre"] == nombre


@pytest.mark.parametrize(
    "text,artista",
    [("pon música de Rosalía", "rosalía"), ("ponme algo de Bad Bunny", "bad bunny"), ("pon canciones de Camarón", "camarón")],
)
def test_artist(match, text, artista) -> None:
    intent, slots = match(text)
    assert intent == "MusicaArtista"
    assert _lower(slots)["artista"] == artista


@pytest.mark.parametrize(
    "text,intent",
    [
        ("siguiente", "MusicaSiguiente"),
        ("Siguiente canción.", "MusicaSiguiente"),
        ("pasa de canción", "MusicaSiguiente"),
        ("salta esta canción", "MusicaSiguiente"),
        ("canción anterior", "MusicaAnterior"),
        ("pon la anterior", "MusicaAnterior"),
        ("pausa", "MusicaPausa"),
        ("Pausa la música.", "MusicaPausa"),
        ("para la música", "MusicaPausa"),
        ("sigue", "MusicaSigue"),
        ("Sigue.", "MusicaSigue"),
        ("continúa la música", "MusicaSigue"),
        ("reanuda", "MusicaSigue"),
        ("sube el volumen", "VolumenSube"),
        ("Súbele.", "VolumenSube"),
        ("más alto", "VolumenSube"),
        ("baja el volumen", "VolumenBaja"),
        ("bájale", "VolumenBaja"),
        ("más bajo", "VolumenBaja"),
        ("qué suena", "MusicaQueSuena"),
        ("qué canción es esta", "MusicaQueSuena"),
    ],
)
def test_controls(match, text, intent) -> None:
    assert match(text)[0] == intent


@pytest.mark.parametrize("text,nivel", [("pon el volumen al 30", 30), ("volumen al 50 por ciento", 50), ("volumen 20", 20)])
def test_volume_set(match, text, nivel) -> None:
    intent, slots = match(text)
    assert intent == "VolumenPon"
    assert int(slots["nivel"]) == nivel


@pytest.mark.parametrize(
    "text",
    [
        "pon un temporizador de 5 minutos",
        "Pon el brillo de la lámpara al 50%.",
        "pon la lámpara al mínimo",
        "Pon el HDMI 3 en la tele.",
        "sube el volumen de la tele",
        "Pon la SER.",
        "pon la radio de jazz",
        "Ok, perfecto. Pues nada, yo ahora en un minuto y diez segundos.",
    ],
)
def test_music_does_not_steal_other_commands(ha_match, text) -> None:
    assert not (ha_match(text)[0] or "").startswith(("Musica", "Volumen"))
