"""script.musica_buscar_y_poner: fuzzy pick of the best Music Assistant result.

The scoring template is rendered with plain jinja2 (only standard filters are
allowed in it, so HA renders it identically).
"""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
HA = REPO / "home-assistant"


def _script() -> dict:
    return yaml.safe_load((HA / "includes" / "scripts.yaml").read_text(encoding="utf-8"))["musica_buscar_y_poner"]


def _var_template(name: str) -> str:
    for step in _script()["sequence"]:
        if "variables" in step and name in step["variables"]:
            return step["variables"][name]
    raise AssertionError(f"variable {name} not found")


def _render(name: str, **ctx) -> str:
    env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols"])
    return env.from_string(_var_template(name)).render(**ctx).strip()


CANDS = [
    {"name": "Despacito - Remix", "artists": [{"name": "Luis Fonsi"}, {"name": "Justin Bieber"}], "uri": "u:remix"},
    {"name": "Despacito", "artists": [{"name": "Luis Fonsi"}, {"name": "Daddy Yankee"}], "uri": "u:orig"},
    {"name": "Despacito (Cover)", "artists": [{"name": "Random Band"}], "uri": "u:cover"},
]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("la canción Despacito", "despacito"),
        ("el tema Malamente", "malamente"),
        ("Hijo de la Luna", "hijo de la luna"),
        ("  ROSALÍA  ", "rosalía"),
    ],
)
def test_strips_spoken_anchor_from_name(raw, expected) -> None:
    assert _render("nombre_limpio", nombre=raw) == expected


def test_prefers_exact_title_with_artist() -> None:
    idx = _render("mejor", cands=CANDS, consulta="despacito de luis fonsi")
    assert int(idx) == 1


def test_accent_and_case_insensitive() -> None:
    cands = [
        {"name": "LA FAMA", "artists": [{"name": "ROSALÍA"}, {"name": "The Weeknd"}], "uri": "a"},
        {"name": "MALAMENTE - Cap.1: Augurio", "artists": [{"name": "ROSALÍA"}], "uri": "b"},
    ]
    assert int(_render("mejor", cands=cands, consulta="malamente de rosalia")) == 1


def test_falls_back_to_first_result_when_nothing_overlaps() -> None:
    assert int(_render("mejor", cands=CANDS, consulta="zzz qqq")) == 0


def test_empty_candidates_gives_minus_one() -> None:
    assert int(_render("mejor", cands=[], consulta="algo")) == -1


def test_plays_on_music_assistant_player_and_returns_what_it_put() -> None:
    blob = yaml.dump(_script(), allow_unicode=True)
    assert "music_assistant.search" in blob
    assert "music_assistant.play_media" in blob
    assert "media_player.satellite1" in blob
    assert "response_variable: resultado" in blob or "response_variable" in blob
    assert "get_library" in blob  # own playlists first


def test_intent_scripts_confirm_by_voice() -> None:
    scripts = yaml.safe_load((HA / "includes" / "intent_scripts.yaml").read_text(encoding="utf-8"))
    for name in ("MusicaCancion", "MusicaDisco", "MusicaPlaylist", "MusicaArtista"):
        s = scripts[name]
        blob = yaml.dump(s, allow_unicode=True)
        assert "script.musica_buscar_y_poner" in blob, name
        assert "Pongo" in blob and "No he encontrado" in blob, name
