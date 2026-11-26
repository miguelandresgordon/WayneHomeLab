"""nlu_live_check: compare HA debug results with versioned expectations."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "infrastructure" / "voice"))

import nlu_live_check  # noqa: E402

EXPECTATIONS = REPO / "home-assistant" / "voice" / "nlu_expectations.yaml"


def test_expectations_file_covers_daily_domains() -> None:
    data = yaml.safe_load(EXPECTATIONS.read_text(encoding="utf-8"))
    intents: set = set()
    for c in data["cases"]:
        intents |= set(c["intent"]) if isinstance(c["intent"], list) else {c["intent"]}
    for needed in ("PonRadioFavorita", "ParaRadioFavorita", "LamparaBrillo", "EnciendeLaLampara", "ApagaLaTele", "HassLightSet"):
        assert needed in intents, needed


def test_evaluate_reports_wrong_intent_and_fuzzy() -> None:
    cases = [
        {"text": "con la lámpara al 50%", "intent": "LamparaBrillo"},
        {"text": "pon la ser", "intent": "PonRadioFavorita"},
        {"text": "hola", "intent": None},
    ]
    results = [
        {"intent": {"name": "PonRadioFavorita"}, "match": False, "source": "custom"},
        {"intent": {"name": "PonRadioFavorita"}, "match": True, "source": "custom"},
        None,
    ]
    failures = nlu_live_check.evaluate(cases, results)
    assert len(failures) == 1
    assert "con la lámpara al 50%" in failures[0]


def test_evaluate_accepts_alternatives() -> None:
    cases = [{"text": "pon la lámpara al 50%", "intent": ["HassLightSet", "LamparaBrillo"]}]
    results = [{"intent": {"name": "HassLightSet"}}]
    assert nlu_live_check.evaluate(cases, results) == []
