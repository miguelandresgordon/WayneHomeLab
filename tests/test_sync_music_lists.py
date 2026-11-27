"""sync_music_lists: library artists/playlists -> hassil lists with spoken variants."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "infrastructure" / "voice" / "music"))

import sync_music_lists as s  # noqa: E402


def test_spoken_variants_strip_accents_symbols_and_emoji() -> None:
    assert "rosalia" in s.spoken_variants("ROSALÍA")
    assert "rosalía" in s.spoken_variants("ROSALÍA")
    assert "asap rocky" in s.spoken_variants("A$AP Rocky")
    assert "c tangana" in s.spoken_variants("C. Tangana")
    assert "alicia y miguel" in s.spoken_variants("Alicia + Miguel")
    assert "camarón" in s.spoken_variants("Camarón 🎸")
    assert "breakbeat andaluz" in s.spoken_variants("👟BREAKBEAT ANDALUZ👟")


def test_unpronounceable_names_are_skipped() -> None:
    assert s.spoken_variants("") == set()
    assert s.spoken_variants("<3") == set()
    assert s.spoken_variants("999999999") == set()


def test_build_lists_yaml_is_valid_hassil(tmp_path: Path) -> None:
    doc = s.build_lists(["ROSALÍA", "A$AP Rocky"], ["Alicia + Miguel", "<3"])
    out = tmp_path / "x.yaml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True))
    data = yaml.safe_load(out.read_text())
    arts = {v["in"]: v["out"] for v in data["lists"]["artista_biblioteca"]["values"]}
    assert arts["rosalia"] == "ROSALÍA" and arts["asap rocky"] == "A$AP Rocky"
    pls = {v["in"]: v["out"] for v in data["lists"]["playlist_biblioteca"]["values"]}
    assert pls == {"alicia y miguel": "Alicia + Miguel", "alicia + miguel": "Alicia + Miguel"} or "alicia y miguel" in pls


def test_generated_file_is_gitignored() -> None:
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "home-assistant/custom_sentences/es/musica_biblioteca.yaml" in gi
