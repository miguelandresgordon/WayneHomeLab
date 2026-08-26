"""Pure speaker-matching logic (no sherpa-onnx dependency)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

UNKNOWN_SPEAKER = "desconocido"
DEFAULT_THRESHOLD = 0.6
DEFAULT_MARGIN = 0.05


@dataclass(frozen=True)
class IdentificationResult:
    person: str
    score: float
    is_known: bool
    second_best_person: str | None = None
    second_best_score: float | None = None


def l2_normalize(embedding: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(embedding)
    if norm == 0.0:
        return embedding
    return embedding / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = l2_normalize(a)
    b_norm = l2_normalize(b)
    return float(np.dot(a_norm, b_norm))


def select_speaker(
    embedding: np.ndarray,
    speakers: dict[str, np.ndarray],
    threshold: float = DEFAULT_THRESHOLD,
    margin: float = DEFAULT_MARGIN,
    unknown_label: str = UNKNOWN_SPEAKER,
) -> IdentificationResult:
    """Pick the best matching speaker using cosine similarity and margin."""
    if not speakers:
        return IdentificationResult(
            person=unknown_label,
            score=0.0,
            is_known=False,
        )

    scores = {
        name: cosine_similarity(embedding, centroid)
        for name, centroid in speakers.items()
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_name, best_score = ranked[0]
    second_name: str | None = None
    second_score: float | None = None

    if len(ranked) > 1:
        second_name, second_score = ranked[1]

    if best_score < threshold:
        return IdentificationResult(
            person=unknown_label,
            score=best_score,
            is_known=False,
            second_best_person=second_name,
            second_best_score=second_score,
        )

    if second_score is not None and (best_score - second_score) < margin:
        return IdentificationResult(
            person=unknown_label,
            score=best_score,
            is_known=False,
            second_best_person=second_name,
            second_best_score=second_score,
        )

    return IdentificationResult(
        person=best_name,
        score=best_score,
        is_known=True,
        second_best_person=second_name,
        second_best_score=second_score,
    )
