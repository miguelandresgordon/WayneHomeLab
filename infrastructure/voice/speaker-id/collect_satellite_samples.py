#!/usr/bin/env python3
"""collect_satellite_samples.py — Copy the Satellite1 WAVs recorded since a
moment into samples/<speaker>/ for enrollment (same mic as real use).

The Assist pipeline stores every command at
/share/assist_pipeline/<pipeline>/<name>/<run>/01_stt-*.wav (Samba: /Volumes/share).

  ./collect_satellite_samples.py --speaker alicia --since 2026-11-27T10:00 --count 12
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = Path("/Volumes/share/assist_pipeline")
MIN_BYTES = 16000 * 2  # >= 1 s of 16 kHz mono PCM16


def select_wavs(root: Path, since: float, limit: int) -> list[Path]:
    wavs = [p for p in root.rglob("01_stt-*.wav") if p.stat().st_mtime >= since and p.stat().st_size >= MIN_BYTES]
    wavs.sort(key=lambda p: p.stat().st_mtime)
    return wavs[:limit]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--speaker", required=True, help="alicia | miguel (minúsculas)")
    ap.add_argument("--since", required=True, help="ISO local time when the session started, e.g. 2026-11-27T10:00")
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--samples-dir", type=Path, default=SCRIPT_DIR / "samples")
    args = ap.parse_args()

    since = dt.datetime.fromisoformat(args.since).timestamp()
    if not args.root.is_dir():
        print(f"No existe {args.root} (¿montado /Volumes/share por Samba?)", file=sys.stderr)
        return 1
    wavs = select_wavs(args.root, since, args.count)
    if not wavs:
        print("No hay WAV nuevos desde esa hora. ¿Dijiste las frases al Satellite1?", file=sys.stderr)
        return 1
    out = args.samples_dir / args.speaker
    out.mkdir(parents=True, exist_ok=True)
    start = len(list(out.glob("*.wav")))
    for i, src in enumerate(wavs, start=start + 1):
        dst = out / f"sat_{i:02d}.wav"
        shutil.copy2(src, dst)
        print(f"{src.parent.name} -> {dst.name}")
    print(f"{len(wavs)} WAV copiados a {out} (total {len(list(out.glob('*.wav')))})")
    if len(wavs) < 8:
        print("AVISO: se recomiendan 8+ clips por persona.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
