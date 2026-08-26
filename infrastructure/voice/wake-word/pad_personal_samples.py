#!/usr/bin/env python3
"""Copy personal wake-word WAVs and append trailing PCM silence.

Assist/STT clips often end at the last voiced sample (0 ms trailing silence).
The trainer's trim_silence.py then reports "Skipped", and Clips(remove_silence=True)
can eat the last phoneme. Padding ~100 ms of zeros keeps the word intact.
"""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path


DEFAULT_PAD_MS = 100


def _is_appledouble(name: str) -> bool:
    return name.startswith("._")


def pad_wav_file(src: Path, dest: Path, pad_ms: int = DEFAULT_PAD_MS) -> None:
    if pad_ms < 0:
        raise ValueError("pad_ms must be >= 0")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(src), "rb") as reader:
        params = reader.getparams()
        frames = reader.readframes(reader.getnframes())
        pad_frames = int(params.framerate * pad_ms / 1000)
        silence = b"\x00" * (pad_frames * params.nchannels * params.sampwidth)
    with wave.open(str(dest), "wb") as writer:
        writer.setparams(params)
        writer.writeframes(frames + silence)


def copy_padded_wavs(
    src_dir: Path,
    dest_dir: Path,
    pad_ms: int = DEFAULT_PAD_MS,
) -> int:
    src_dir = Path(src_dir)
    dest_dir = Path(dest_dir)
    if not src_dir.is_dir():
        return 0

    wavs = sorted(
        p
        for p in src_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".wav" and not _is_appledouble(p.name)
    )
    if not wavs:
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for index, wav in enumerate(wavs):
        dest = dest_dir / f"personal_{index:03d}.wav"
        pad_wav_file(wav, dest, pad_ms=pad_ms)
        copied += 1
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src_dir", type=Path)
    parser.add_argument("dest_dir", type=Path)
    parser.add_argument("--pad-ms", type=int, default=DEFAULT_PAD_MS)
    args = parser.parse_args(argv)
    copied = copy_padded_wavs(args.src_dir, args.dest_dir, pad_ms=args.pad_ms)
    print(f"padded_personal_wavs={copied} dest={args.dest_dir} pad_ms={args.pad_ms}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
