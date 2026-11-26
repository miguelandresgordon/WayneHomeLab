"""Shared hassil fixture: all custom sentences under home-assistant/custom_sentences/es."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from hassil import Intents, recognize

REPO_ROOT = Path(__file__).resolve().parents[2]
SENTENCES_DIR = REPO_ROOT / "home-assistant" / "custom_sentences" / "es"


def load_custom_intents() -> Intents:
    merged: dict = {"language": "es", "intents": {}, "lists": {}, "expansion_rules": {}}
    for path in sorted(SENTENCES_DIR.glob("*.yaml")):
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
        res = recognize(text, custom_intents)
        if res is None:
            return None, {}
        return res.intent.name, {k: v.value for k, v in res.entities.items()}

    return _match
