#!/usr/bin/env python3
"""prepare_retrain_negatives.py — Build the negative set for retraining
«Mariano» (does NOT train and does NOT spend anything).

  ./prepare_retrain_negatives.py --false-wakes --transcripts transcripts.jsonl
  ./prepare_retrain_negatives.py --streams            # records retrain_negatives.yaml URLs
  ./prepare_retrain_negatives.py --summary

Output: retrain_data/negatives/<kind>/*.wav (16 kHz mono PCM16, gitignored).
Then: train_mariano_runpod.sh / setup_trainer_windows.ps1 upload them as
negative_samples (see docs/wake-word-mariano.md, «Reentrenamiento F3»).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "retrain_data" / "negatives"
ASSIST_ROOT = Path("/Volumes/share/assist_pipeline")
MANIFEST = HERE / "retrain_negatives.yaml"


def select_false_wakes(rows: list[dict], min_dur_s: float, is_command: Callable[[str], bool]) -> list[dict]:
    """Long clips whose transcript is not a command = false wake-word triggers."""
    return [r for r in rows if r["dur_s"] >= min_dur_s and not is_command(r.get("text", ""))]


def chunk_plan(total_s: int, clip_s: int) -> list[tuple[int, int]]:
    return [(start, min(clip_s, total_s - start)) for start in range(0, total_s, clip_s)]


def ffmpeg_record_cmd(url: str, pattern: str, seconds: int, clip_s: int) -> list[str]:
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", url, "-t", str(seconds), "-vn",
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        "-f", "segment", "-segment_time", str(clip_s), pattern,
    ]


def _command_matcher() -> Callable[[str], bool]:
    """Use the repo's own custom sentences (hassil) to decide what is a command."""
    sys.path.insert(0, str(HERE.parents[2] / "tests" / "assist"))
    from conftest import load_custom_intents  # type: ignore
    from hassil import recognize_best

    intents = load_custom_intents()
    return lambda t: recognize_best(t, intents, language="es") is not None


def false_wakes(transcripts: Path, min_dur_s: float) -> int:
    rows = []
    for line in transcripts.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows.append({"run": r["run"], "dur_s": r["dur_s"], "text": r["stt"].get("text", "")})
    picked = select_false_wakes(rows, min_dur_s, _command_matcher())
    dest = OUT / "voz_alta"
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in picked:
        src = next(ASSIST_ROOT.rglob(f"{r['run']}/01_stt-*.wav"), None)
        if src:
            shutil.copy2(src, dest / f"falsewake_{r['run']}.wav")
            n += 1
    print(f"voz_alta: {n} activaciones falsas reales copiadas")
    return n


def streams(manifest: dict) -> None:
    clip = int(manifest.get("clip_seconds", 10))
    for s in manifest["sources"]:
        if not s.get("url"):
            continue
        dest = OUT / s["kind"]
        dest.mkdir(parents=True, exist_ok=True)
        cmd = ffmpeg_record_cmd(s["url"], str(dest / f"{s['name']}_%04d.wav"), int(s["minutes"]) * 60, clip)
        print(f"grabando {s['name']} ({s['minutes']} min) -> {dest}")
        subprocess.run(cmd, check=False)


def summary() -> None:
    for d in sorted(OUT.glob("*")):
        wavs = list(d.glob("*.wav"))
        print(f"{d.name:12} {len(wavs):5} WAV  {sum(w.stat().st_size for w in wavs) / 32000 / 60:6.1f} min")


def main() -> int:
    import yaml

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--false-wakes", action="store_true")
    ap.add_argument("--transcripts", type=Path, help="JSONL from the F0 re-transcription (run, dur_s, stt.text)")
    ap.add_argument("--streams", action="store_true")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if args.false_wakes:
        if not args.transcripts:
            sys.exit("--false-wakes needs --transcripts")
        min_dur = next(s["min_dur_s"] for s in manifest["sources"] if s.get("from") == "assist_false_wakes")
        false_wakes(args.transcripts, min_dur)
    if args.streams:
        streams(manifest)
    if args.summary or not (args.false_wakes or args.streams):
        summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
