"""spotify_probe: track-change latency from HA state timeline (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "infrastructure" / "voice" / "music"))

import spotify_probe as sp  # noqa: E402


def S(t, title, state="playing", pos=None):
    return sp.Sample(t=t, title=title, state=state, position=pos)


def test_latency_is_time_until_new_title_is_playing() -> None:
    tl = [S(0.0, "A"), S(0.5, "A"), S(1.2, "B", "buffering"), S(2.4, "B", "playing")]
    assert sp.switch_latency(tl, t_cmd=0.0, old_title="A") == pytest.approx(2.4)


def test_position_reset_counts_as_audible_start() -> None:
    # title changes immediately but audio starts when position starts moving
    tl = [S(0.0, "A", pos=100), S(0.3, "B", pos=0), S(1.0, "B", pos=0), S(3.1, "B", pos=1)]
    assert sp.switch_latency(tl, t_cmd=0.0, old_title="A", use_position=True) == pytest.approx(3.1)


def test_never_switches_returns_none() -> None:
    assert sp.switch_latency([S(0, "A"), S(10, "A")], t_cmd=0.0, old_title="A") is None


def test_summary_with_threshold() -> None:
    s = sp.summarize([1.5, 2.0, 2.5, None], threshold_s=2.0)
    assert s["n"] == 4 and s["failed"] == 1
    assert s["median_s"] == pytest.approx(2.0)
    assert s["pass"] is False


def test_count_retry_lines_in_ma_logs() -> None:
    log = "\n".join([
        "2026-11-26 11:22:24.491 INFO (MainThread) [music_assistant.Spotify] Attempt 2/5 failed: Spotify Rate Limiter",
        "2026-11-26 11:22:35.351 INFO (MainThread) [music_assistant.Spotify] Attempt 3/5 failed: Spotify Rate Limiter",
        "2026-11-26 11:22:36.000 INFO (MainThread) [music_assistant] something else",
    ])
    assert sp.count_retries(log) == {"Attempt 2": 1, "Attempt 3": 1}
