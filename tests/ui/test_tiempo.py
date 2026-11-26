"""Tiempo: AEMET with own modern charts, light for the Pi (no containers, bounded history)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
HA = REPO / "home-assistant"
DASH = HA / "dashboards" / "tiempo.yaml"


def _pkg() -> dict:
    return yaml.safe_load((HA / "packages" / "tiempo.yaml").read_text(encoding="utf-8"))


def test_forecast_sensor_caches_hourly_and_daily_compactly() -> None:
    blob = yaml.dump(_pkg(), allow_unicode=True)
    assert "weather.get_forecasts" in blob and "weather.aemet" in blob
    assert "hourly" in blob and "daily" in blob
    assert "sensor.aemet_prevision" in blob
    # only the fields the charts need (keeps recorder rows small)
    assert "temperature" in blob and "precipitation_probability" in blob and "templow" in blob
    trig = yaml.dump(_pkg()["template"][0]["triggers"])
    assert "minutes" in trig  # periodic, not every state change


def _cards(node):
    if isinstance(node, dict):
        if "type" in node:
            yield node
        for v in node.values():
            yield from _cards(v)
    elif isinstance(node, list):
        for v in node:
            yield from _cards(v)


def test_uses_apexcharts_not_the_basic_weather_card() -> None:
    d = yaml.safe_load(DASH.read_text(encoding="utf-8"))
    types = [c["type"] for c in _cards(d)]
    assert types.count("custom:apexcharts-card") >= 3
    assert "weather-forecast" not in types


def test_history_queries_are_bounded() -> None:
    d = yaml.safe_load(DASH.read_text(encoding="utf-8"))
    for c in _cards(d):
        if c["type"] == "custom:apexcharts-card":
            span = str(c.get("graph_span", ""))
            m = re.fullmatch(r"(\d+)(h|d)", span)
            assert m, f"graph_span missing/invalid: {span!r}"
            hours = int(m.group(1)) * (24 if m.group(2) == "d" else 1)
            assert hours <= 7 * 24
            for s in c.get("series", []):
                if hours > 48 and "data_generator" not in s:
                    assert "statistics" in s, "long spans must use long-term statistics"


def test_big_numbers_for_current_conditions() -> None:
    b = DASH.read_text(encoding="utf-8")
    for e in ("sensor.aemet_temperature", "sensor.aemet_temperature_feeling", "sensor.aemet_humidity", "sensor.aemet_wind_speed", "sensor.aemet_rain_probability"):
        assert e in b, e
