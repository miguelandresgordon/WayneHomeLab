"""TDD tests for padding trailing silence on personal wake-word WAVs."""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import pytest

WAKE_WORD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WAKE_WORD_DIR))

import pad_personal_samples as pad_mod  # noqa: E402


def _write_sine_wav(path: Path, *, duration_s: float = 0.25, sr: int = 16000) -> int:
    """Write a non-silent mono PCM16 WAV; returns frame count."""
    import math
    import struct

    nframes = int(sr * duration_s)
    frames = bytearray()
    for i in range(nframes):
        sample = int(12000 * math.sin(2 * math.pi * 440 * i / sr))
        frames.extend(struct.pack("<h", sample))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(frames))
    return nframes


def test_pad_duration_adds_requested_silence(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    _write_sine_wav(src / "clip.wav", duration_s=0.20, sr=16000)

    copied = pad_mod.copy_padded_wavs(src, dest, pad_ms=100)

    assert copied == 1
    with wave.open(str(dest / "personal_000.wav"), "rb") as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1
        duration_ms = 1000.0 * wf.getnframes() / wf.getframerate()
    assert duration_ms == pytest.approx(300.0, abs=2.0)


def test_pad_keeps_original_audio_prefix(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    nframes = _write_sine_wav(src / "clip.wav", duration_s=0.10, sr=16000)
    with wave.open(str(src / "clip.wav"), "rb") as wf:
        original = wf.readframes(nframes)

    pad_mod.copy_padded_wavs(src, dest, pad_ms=80)

    with wave.open(str(dest / "personal_000.wav"), "rb") as wf:
        prefix = wf.readframes(nframes)
        trailing = wf.readframes(wf.getnframes())
    assert prefix == original
    assert trailing == b"\x00" * len(trailing)
    assert len(trailing) > 0


def test_pad_skips_appledouble_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    _write_sine_wav(src / "keep.wav")
    (src / "._keep.wav").write_bytes(b"not-a-wav")

    copied = pad_mod.copy_padded_wavs(src, dest, pad_ms=50)

    assert copied == 1
    assert list(dest.glob("*.wav")) == [dest / "personal_000.wav"]


def test_missing_src_returns_zero(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    copied = pad_mod.copy_padded_wavs(tmp_path / "nope", dest, pad_ms=100)
    assert copied == 0
    assert not dest.exists() or not any(dest.glob("*.wav"))
