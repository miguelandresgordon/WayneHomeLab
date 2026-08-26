#!/usr/bin/env python3
"""Train speaker profiles locally on the Mac (no Colab required).

Reads WAV clips from ``samples/<person>/``, computes embeddings with sherpa-onnx,
and writes export artefacts to ``export/``.

Usage:
  pip3 install sherpa-onnx soundfile numpy
  python3 train_profiles.py
  python3 train_profiles.py --speakers miguel ana

Output (in ``export/``):
  speaker_profiles.json
  config.json
  wespeaker_en_voxceleb_resnet34.onnx
  speaker-id-mariano-export.zip
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SAMPLES_DIR = SCRIPT_DIR / "samples"
DEFAULT_EXPORT_DIR = SCRIPT_DIR / "export"
DEFAULT_MODELS_DIR = SCRIPT_DIR / "models"

MODEL_NAME = "wespeaker_en_voxceleb_resnet34.onnx"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    "speaker-recongition-models/wespeaker_en_voxceleb_resnet34.onnx"
)
DEFAULT_THRESHOLD = 0.6
DEFAULT_MARGIN = 0.05


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sample_rate = sf.read(path, always_2d=True, dtype="float32")
    return np.ascontiguousarray(data[:, 0]), sample_rate


def l2_normalize(embedding: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(embedding)
    return embedding if norm == 0.0 else embedding / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(l2_normalize(a), l2_normalize(b)))


def download_model(model_path: Path) -> None:
    if model_path.is_file():
        return
    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando modelo (~25 MB) → {model_path}")
    try:
        urllib.request.urlretrieve(MODEL_URL, model_path)
    except Exception:
        # Fallback: curl evita problemas SSL en Python macOS
        import subprocess
        result = subprocess.run(
            ["curl", "-fsSL", "-o", str(model_path), MODEL_URL],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Download failed: {result.stderr}") from None
    print("Modelo descargado.")


def list_speakers(samples_dir: Path) -> list[str]:
    if not samples_dir.is_dir():
        return []
    return sorted(
        name
        for name in (p.name for p in samples_dir.iterdir() if p.is_dir())
        if list((samples_dir / name).glob("*.wav"))
    )


def list_wavs(samples_dir: Path, speaker: str) -> list[Path]:
    return sorted((samples_dir / speaker).glob("*.wav"))


def compute_embedding(
    wav_path: Path,
    extractor: sherpa_onnx.SpeakerEmbeddingExtractor,
) -> np.ndarray:
    samples, sample_rate = load_audio(wav_path)
    stream = extractor.create_stream()
    stream.accept_waveform(sample_rate=sample_rate, waveform=samples)
    stream.input_finished()
    if not extractor.is_ready(stream):
        raise RuntimeError(f"Extractor not ready for {wav_path}")
    return l2_normalize(np.asarray(extractor.compute(stream), dtype=np.float32))


def compute_centroid(
    wav_files: list[Path],
    extractor: sherpa_onnx.SpeakerEmbeddingExtractor,
) -> np.ndarray:
    embeddings = [compute_embedding(path, extractor) for path in wav_files]
    return l2_normalize(np.mean(np.stack(embeddings, axis=0), axis=0))


def estimate_threshold(genuine: list[float], impostor: list[float]) -> float:
    """Calibrate threshold; handles single-speaker (no impostor pairs)."""
    if impostor:
        thresholds = np.linspace(0.0, 1.0, 200)
        best_threshold = DEFAULT_THRESHOLD
        best_distance = 1.0
        for threshold in thresholds:
            far = sum(score >= threshold for score in impostor) / len(impostor)
            frr = sum(score < threshold for score in genuine) / len(genuine)
            distance = abs(far - frr)
            if distance < best_distance:
                best_distance = distance
                best_threshold = float(threshold)
        return max(best_threshold, DEFAULT_THRESHOLD)

    # Single speaker: floor from genuine score distribution (5th percentile - margin)
    if not genuine:
        return DEFAULT_THRESHOLD
    floor = max(DEFAULT_THRESHOLD, float(np.percentile(genuine, 5)) - 0.05)
    return round(min(floor, 0.85), 4)


def export_zip(export_dir: Path, files: list[Path]) -> Path:
    zip_path = export_dir / "speaker-id-mariano-export.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.name)
    return zip_path


def train(
    speakers: list[str],
    samples_dir: Path,
    export_dir: Path,
    models_dir: Path,
    margin: float,
) -> Path:
    model_path = models_dir / MODEL_NAME
    download_model(model_path)

    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(model_path),
        num_threads=2,
        debug=False,
        provider="cpu",
    )
    if not config.validate():
        raise ValueError("Invalid sherpa-onnx config")
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
    embedding_dim = extractor.dim

    centroids: dict[str, np.ndarray] = {}
    clip_counts: dict[str, int] = {}

    for speaker in speakers:
        wavs = list_wavs(samples_dir, speaker)
        if not wavs:
            raise ValueError(f"No WAV files for speaker '{speaker}' in {samples_dir / speaker}")
        if len(wavs) < 3:
            print(f"AVISO: {speaker} tiene solo {len(wavs)} clips (recomendado 8+)")
        print(f"  {speaker}: {len(wavs)} clip(s) → embedding...")
        centroids[speaker] = compute_centroid(wavs, extractor)
        clip_counts[speaker] = len(wavs)

    genuine: list[float] = []
    impostor: list[float] = []
    for speaker in speakers:
        centroid = centroids[speaker]
        for wav_path in list_wavs(samples_dir, speaker):
            embedding = compute_embedding(wav_path, extractor)
            genuine.append(cosine_similarity(embedding, centroid))
        for other, other_centroid in centroids.items():
            if other == speaker:
                continue
            for wav_path in list_wavs(samples_dir, speaker):
                embedding = compute_embedding(wav_path, extractor)
                impostor.append(cosine_similarity(embedding, other_centroid))

    threshold = estimate_threshold(genuine, impostor)
    print(f"Umbral calibrado: {threshold} (genuine min={min(genuine):.3f}, mean={np.mean(genuine):.3f})")

    profiles = {
        "version": 1,
        "model": MODEL_NAME,
        "embedding_dim": embedding_dim,
        "threshold": threshold,
        "margin": margin,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "speakers": {
            name: {
                "centroid": centroid.tolist(),
                "clip_count": clip_counts[name],
            }
            for name, centroid in centroids.items()
        },
    }

    config_data = {
        "model": MODEL_NAME,
        "threshold": threshold,
        "margin": margin,
        "speakers": speakers,
    }

    export_dir.mkdir(parents=True, exist_ok=True)
    profiles_path = export_dir / "speaker_profiles.json"
    config_path = export_dir / "config.json"
    model_export = export_dir / MODEL_NAME

    profiles_path.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    shutil.copy2(model_path, model_export)

    zip_path = export_zip(export_dir, [profiles_path, config_path, model_export])
    zip_mb = zip_path.stat().st_size / (1024 * 1024)

    print(f"\nExport listo en: {export_dir.resolve()}")
    print(f"  speaker_profiles.json")
    print(f"  config.json")
    print(f"  {MODEL_NAME}")
    print(f"  speaker-id-mariano-export.zip ({zip_mb:.1f} MB)")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--speakers",
        nargs="*",
        help="Personas a enrolar (default: subcarpetas con WAV en samples/)",
    )
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    args = parser.parse_args()

    speakers = args.speakers or list_speakers(args.samples_dir)
    if not speakers:
        print(f"ERROR: no hay muestras en {args.samples_dir}/<persona>/*.wav", file=sys.stderr)
        print("Graba primero con: python3 record_samples.py --speaker miguel --count 10", file=sys.stderr)
        return 1

    print(f"Entrenando perfiles para: {', '.join(speakers)}")
    try:
        train(
            speakers=speakers,
            samples_dir=args.samples_dir,
            export_dir=args.export_dir,
            models_dir=args.models_dir,
            margin=args.margin,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
