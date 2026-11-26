"""Radio stability probe: pure analysis of sampled player states (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "infrastructure" / "voice" / "radio"))

import radio_probe  # noqa: E402


def _samples(spec: list[tuple[float, str]]) -> list[radio_probe.Sample]:
    return [radio_probe.Sample(t=t, state=s) for t, s in spec]


def test_clean_run_has_no_drops_and_measures_start_latency() -> None:
    s = _samples([(0.0, "idle"), (1.0, "idle"), (2.5, "playing")] + [(2.5 + i, "playing") for i in range(1, 60)])
    r = radio_probe.analyze(s, t_command=0.0)
    assert r.start_latency_s == pytest.approx(2.5)
    assert r.drops == 0
    assert r.longest_gap_s == 0
    assert r.play_ratio == pytest.approx(1.0)


def test_drop_and_recovery_are_counted_with_gap_length() -> None:
    spec = [(0.0, "idle"), (2.0, "playing"), (10.0, "playing"), (11.0, "idle"), (150.0, "idle"), (151.0, "playing"), (200.0, "playing")]
    r = radio_probe.analyze(_samples(spec), t_command=0.0)
    assert r.drops == 1
    assert r.longest_gap_s == pytest.approx(140.0)
    assert r.total_gap_s == pytest.approx(140.0)
    assert r.play_ratio < 0.4


def test_never_starts_is_reported() -> None:
    r = radio_probe.analyze(_samples([(0.0, "idle"), (30.0, "idle")]), t_command=0.0)
    assert r.start_latency_s is None
    assert r.drops == 0
    assert r.play_ratio == 0.0


def test_unavailable_counts_as_gap() -> None:
    spec = [(0.0, "idle"), (1.0, "playing"), (5.0, "unavailable"), (8.0, "playing"), (20.0, "playing")]
    r = radio_probe.analyze(_samples(spec), t_command=0.0)
    assert r.drops == 1
    assert r.longest_gap_s == pytest.approx(3.0)


@pytest.mark.parametrize(
    ("latency", "drops", "expected"),
    [(2.0, 0, True), (9.0, 0, False), (2.0, 1, False), (None, 0, False)],
)
def test_verdict_applies_explicit_thresholds(latency, drops, expected) -> None:
    th = radio_probe.Thresholds(max_start_latency_s=5.0, max_drops=0)
    r = radio_probe.Result(start_latency_s=latency, drops=drops, total_gap_s=0.0, longest_gap_s=0.0, play_ratio=1.0, duration_s=1800.0)
    assert radio_probe.verdict(r, th)[0] is expected
