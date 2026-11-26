#!/usr/bin/env python3
"""sync_music_lists.py — Turn your Music Assistant library (artists and
playlists) into hassil lists so «pon X de <artista>» and «pon mi playlist
<nombre>» match names Groq can actually say.

Writes home-assistant/custom_sentences/es/musica_biblioteca.yaml (gitignored:
it is personal library data) and, with --deploy, copies it to HAOS and reloads
the conversation agent.

  ./sync_music_lists.py --deploy
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "home-assistant" / "custom_sentences" / "es" / "musica_biblioteca.yaml"
HA_URL = os.environ.get("HA_URL", "http://192.168.1.110:8123")
HAOS_SSH = os.environ.get("HAOS_SSH", "root@192.168.1.110")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def spoken_variants(name: str) -> set[str]:
    """Lowercase forms a speech-to-text engine could produce for `name`."""
    base = name.lower().replace("$", "s").replace("&", " y ").replace("+", " y ")
    base = "".join(c if (c.isalnum() or c.isspace() or c in "'ñáéíóúü") else " " for c in base)
    base = re.sub(r"\s+", " ", base).strip()
    letters = re.sub(r"[^a-záéíóúüñ]", "", base)
    if len(letters) < 2:  # «<3», «999999999», emoji-only…
        return set()
    out = {base, _strip_accents(base)}
    raw = re.sub(r"\s+", " ", name.lower()).strip()
    if raw and all(c.isalnum() or c.isspace() or c in "'+" for c in raw):
        out.add(raw)
    return {v for v in out if v}


def build_lists(artists: list[str], playlists: list[str]) -> dict:
    def values(names: list[str]) -> list[dict]:
        seen: dict[str, str] = {}
        for n in names:
            for v in sorted(spoken_variants(n)):
                seen.setdefault(v, n)
        return [{"in": k, "out": v} for k, v in sorted(seen.items())]

    return {
        "language": "es",
        "lists": {
            "artista_biblioteca": {"values": values(artists)},
            "playlist_biblioteca": {"values": values(playlists)},
        },
    }


def _library_items(session, media_type: str) -> list[dict]:
    r = session.post(
        f"{HA_URL}/api/services/music_assistant/get_library?return_response",
        json={"config_entry_id": _ma_entry(session), "media_type": media_type, "limit": 1000},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["service_response"]["items"]


def _library(session, media_type: str) -> list[str]:
    return [i["name"] for i in _library_items(session, media_type) if i.get("name")]


def _all_artists(session) -> list[str]:
    """Followed artists + artists of saved albums and tracks."""
    names = set(_library(session, "artist"))
    for mt in ("album", "track"):
        for item in _library_items(session, mt):
            names.update(a["name"] for a in item.get("artists") or [] if a.get("name"))
    return sorted(names)


def _ma_entry(session) -> str:
    entries = session.get(f"{HA_URL}/api/config/config_entries/entry", params={"domain": "music_assistant"}, timeout=10).json()
    return entries[0]["entry_id"]


def main() -> int:
    import requests
    import yaml

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()
    tok = os.environ.get("HA_TOKEN", "").strip()
    p = Path.home() / ".config" / "wayne" / "ha_token"
    if not tok and p.is_file():
        tok = p.read_text().strip()
    if not tok:
        sys.exit("HA token missing")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    doc = build_lists(_all_artists(s), _library(s, "playlist"))
    header = "# GENERADO por infrastructure/voice/music/sync_music_lists.py — no editar ni commitear\n"
    OUT.write_text(header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    n_a = len(doc["lists"]["artista_biblioteca"]["values"])
    n_p = len(doc["lists"]["playlist_biblioteca"]["values"])
    print(f"{OUT.name}: {n_a} variantes de artista, {n_p} de playlist")
    if args.deploy:
        subprocess.run(["scp", "-q", str(OUT), f"{HAOS_SSH}:/config/custom_sentences/es/{OUT.name}"], check=True)
        s.post(f"{HA_URL}/api/services/conversation/reload", timeout=30).raise_for_status()
        print("desplegado y conversación recargada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
