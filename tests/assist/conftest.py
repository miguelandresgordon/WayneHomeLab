"""Shared hassil fixture: all custom sentences under home-assistant/custom_sentences/es."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from hassil import Intents, recognize_best

REPO_ROOT = Path(__file__).resolve().parents[2]
SENTENCES_DIR = REPO_ROOT / "home-assistant" / "custom_sentences" / "es"


def sentence_files() -> list[Path]:
    """Versioned sentences + the library lists (real file if generated, else the template)."""
    files = sorted(SENTENCES_DIR.glob("*.yaml"))
    if not (SENTENCES_DIR / "musica_biblioteca.yaml").is_file():
        files.append(SENTENCES_DIR / "musica_biblioteca.yaml.example")
    return files


def load_custom_intents() -> Intents:
    merged: dict = {"language": "es", "intents": {}, "lists": {}, "expansion_rules": {}}
    for path in sentence_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for key in ("intents", "lists", "expansion_rules"):
            for name, value in (data.get(key) or {}).items():
                if key == "intents" and name in merged["intents"]:
                    merged["intents"][name]["data"].extend(value["data"])
                else:
                    merged[key][name] = value
    return Intents.from_dict(merged)


@pytest.fixture(scope="session")
def custom_intents() -> Intents:
    return load_custom_intents()


@pytest.fixture(scope="session")
def match(custom_intents: Intents):
    """match(text) -> (intent_name, {slot: value}) or (None, {})."""

    def _match(text: str) -> tuple[str | None, dict]:
        # Same ranking as HA (fewer wildcards / more literal text first).
        res = recognize_best(text, custom_intents, language="es")
        if res is None:
            return None, {}
        return res.intent.name, {k: v.value for k, v in res.entities.items()}

    return _match


# --------------------------------------------------------------------------- #
# HA-faithful simulator: built-in HA intents (home-assistant-intents, es) +
# our custom sentences, ranked exactly like HA's DefaultAgent
# (custom sentences first, then non-wildcard {name}, then fewer wildcards).
# --------------------------------------------------------------------------- #
EXPOSED_NAMES = [
    ("lámpara", "light.yeelink_mono6_6409_light", "light"),
    ("tele", "media_player.tv_ga_2", "media_player"),
    ("satellite1", "media_player.satellite1", "media_player"),
]


@pytest.fixture(scope="session")
def ha_match():
    import copy

    home_assistant_intents = pytest.importorskip("home_assistant_intents")
    from hassil import recognize_best
    from hassil.intents import TextSlotList

    base = copy.deepcopy(home_assistant_intents.get_intents("es"))
    for path in sentence_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for name, value in (data.get("intents") or {}).items():
            blocks = copy.deepcopy(value["data"])
            for blk in blocks:
                blk.setdefault("metadata", {})["hass_custom_sentence"] = True
            base["intents"].setdefault(name, {"data": []})["data"].extend(blocks)
        base["lists"].update(data.get("lists") or {})
        base.setdefault("expansion_rules", {}).update(data.get("expansion_rules") or {})
    intents = Intents.from_dict(base)
    lists = {
        "name": TextSlotList.from_tuples([(n, e, {"domain": d}) for n, e, d in EXPOSED_NAMES]),
        "area": TextSlotList.from_strings(["salón", "dormitorio"]),
        "floor": TextSlotList.from_strings(["planta baja"]),
    }

    def _match(text: str) -> tuple[str | None, dict]:
        res = recognize_best(
            text,
            intents,
            slot_lists=lists,
            best_metadata_key="hass_custom_sentence",
            best_slot_name="name",
            language="es",
        )
        if res is None:
            return None, {}
        return res.intent.name, {k: v.value for k, v in res.entities.items()}

    return _match
