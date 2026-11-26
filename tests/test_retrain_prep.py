"""F3c: retraining prep (not launched) — negatives manifest, false-wake picker, stream chunker."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WW = REPO / "infrastructure" / "voice" / "wake-word"
sys.path.insert(0, str(WW))

import prepare_retrain_negatives as p  # noqa: E402


def test_manifest_covers_tv_loud_voice_radio_and_music() -> None:
    m = yaml.safe_load((WW / "retrain_negatives.yaml").read_text(encoding="utf-8"))
    kinds = {s["kind"] for s in m["sources"]}
    assert {"tv_es", "voz_alta", "radio_habla", "musica"} <= kinds
    for s in m["sources"]:
        if s.get("url"):
            assert s["url"].startswith("https://")
            assert 0 < s["minutes"] <= 60


def test_false_wakes_are_long_non_command_clips() -> None:
    rows = [
        {"run": "a", "dur_s": 9.0, "text": "Hola, amigo. Voy a mirar si desde Database..."},
        {"run": "b", "dur_s": 2.4, "text": "Pon la SER."},
        {"run": "c", "dur_s": 7.5, "text": "Pon el brillo de la lámpara al 50%."},
        {"run": "d", "dur_s": 12.0, "text": "Y la deja al mando del general..."},
    ]
    is_command = lambda t: t.startswith("Pon")  # noqa: E731
    picked = p.select_false_wakes(rows, min_dur_s=6.0, is_command=is_command)
    assert [r["run"] for r in picked] == ["a", "d"]


def test_chunk_plan_splits_minutes_into_fixed_clips() -> None:
    plan = p.chunk_plan(total_s=65, clip_s=10)
    assert plan[0] == (0, 10) and plan[-1] == (60, 5)
    assert sum(d for _, d in plan) == 65


def test_ffmpeg_command_is_16k_mono_pcm() -> None:
    cmd = p.ffmpeg_record_cmd("https://x/stream.mp3", "/tmp/out_%03d.wav", seconds=30, clip_s=10)
    joined = " ".join(cmd)
    assert "-ar 16000" in joined and "-ac 1" in joined and "pcm_s16le" in joined
    assert "-t 30" in joined and "-segment_time 10" in joined


def test_outputs_are_gitignored() -> None:
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "infrastructure/voice/wake-word/retrain_data/" in gi


def test_capture_script_for_positives_exists() -> None:
    sh = (WW / "record_wake_samples.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in sh and "16000" in sh and "personal_samples" in sh
    guion = (WW / "guion_muestras_mariano.md").read_text(encoding="utf-8").lower()
    for needle in ("alicia", "miguel", "radio", "tele", "voz alta", "mariano"):
        assert needle in guion, needle
