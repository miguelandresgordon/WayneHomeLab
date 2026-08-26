"""Speaker recognition — embedding extraction and profile matching."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import sherpa_onnx
import soundfile as sf

from core import (
    DEFAULT_MARGIN,
    DEFAULT_THRESHOLD,
    UNKNOWN_SPEAKER,
    IdentificationResult,
    l2_normalize,
    select_speaker,
)

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_MARGIN",
    "DEFAULT_THRESHOLD",
    "UNKNOWN_SPEAKER",
    "IdentificationResult",
    "SpeakerRecognizer",
    "cosine_similarity",
    "l2_normalize",
    "load_audio",
    "select_speaker",
]

# Re-export for backward compatibility
from core import cosine_similarity  # noqa: E402


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sample_rate = sf.read(path, always_2d=True, dtype="float32")
    samples = np.ascontiguousarray(data[:, 0])
    return samples, sample_rate


class SpeakerRecognizer:
    """Loads sherpa-onnx model + enrolled speaker profiles."""

    def __init__(
        self,
        model_path: Path,
        profiles_path: Path,
        threshold: float | None = None,
        margin: float | None = None,
        num_threads: int = 1,
    ) -> None:
        self.model_path = model_path
        self.profiles_path = profiles_path
        self.num_threads = num_threads
        self.threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
        self.margin = margin if margin is not None else DEFAULT_MARGIN
        self._extractor: sherpa_onnx.SpeakerEmbeddingExtractor | None = None
        self._profiles_data: dict[str, Any] = {}
        self._speaker_centroids: dict[str, np.ndarray] = {}

    @property
    def speaker_names(self) -> list[str]:
        return sorted(self._speaker_centroids.keys())

    def load(self) -> None:
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not self.profiles_path.is_file():
            raise FileNotFoundError(f"Profiles not found: {self.profiles_path}")

        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(self.model_path),
            num_threads=self.num_threads,
            debug=False,
            provider="cpu",
        )
        if not config.validate():
            raise ValueError(f"Invalid sherpa-onnx config for model {self.model_path}")

        self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        self._load_profiles()

    def reload_profiles(self) -> None:
        self._load_profiles()

    def _load_profiles(self) -> None:
        with self.profiles_path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        self._profiles_data = data
        if self.threshold is None:
            self.threshold = float(data.get("threshold", DEFAULT_THRESHOLD))
        if self.margin is None:
            self.margin = float(data.get("margin", DEFAULT_MARGIN))

        speakers_raw = data.get("speakers", {})
        centroids: dict[str, np.ndarray] = {}
        for name, profile in speakers_raw.items():
            centroid = np.asarray(profile["centroid"], dtype=np.float32)
            centroids[name] = l2_normalize(centroid)

        self._speaker_centroids = centroids
        logger.info(
            "Loaded %d speaker profile(s) from %s",
            len(self._speaker_centroids),
            self.profiles_path,
        )

    def compute_embedding(self, wav_path: Path) -> np.ndarray:
        if self._extractor is None:
            raise RuntimeError("Recognizer not loaded — call load() first")

        samples, sample_rate = load_audio(wav_path)
        stream = self._extractor.create_stream()
        stream.accept_waveform(sample_rate=sample_rate, waveform=samples)
        stream.input_finished()

        if not self._extractor.is_ready(stream):
            raise RuntimeError(f"Embedding extractor not ready for {wav_path}")

        embedding = np.asarray(self._extractor.compute(stream), dtype=np.float32)
        return l2_normalize(embedding)

    def identify_file(self, wav_path: Path) -> IdentificationResult:
        embedding = self.compute_embedding(wav_path)
        return select_speaker(
            embedding=embedding,
            speakers=self._speaker_centroids,
            threshold=self.threshold,
            margin=self.margin,
        )

    def health(self) -> dict[str, Any]:
        return {
            "model_path": str(self.model_path),
            "profiles_path": str(self.profiles_path),
            "model_exists": self.model_path.is_file(),
            "profiles_exists": self.profiles_path.is_file(),
            "speaker_count": len(self._speaker_centroids),
            "speakers": self.speaker_names,
            "threshold": self.threshold,
            "margin": self.margin,
            "extractor_loaded": self._extractor is not None,
        }
