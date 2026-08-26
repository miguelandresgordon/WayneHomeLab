"""Tests for speaker recognition core (pure math + selection logic)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ADDON_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ADDON_DIR.parents[2]
SPEAKER_ID_DIR = REPO_ROOT / "infrastructure" / "voice" / "speaker-id"

sys.path.insert(0, str(ADDON_DIR))
sys.path.insert(0, str(SPEAKER_ID_DIR))

from core import UNKNOWN_SPEAKER, cosine_similarity, l2_normalize, select_speaker  # noqa: E402
from validate_profiles import validate_profiles  # noqa: E402


def _unit_vector(index: int, size: int = 8) -> np.ndarray:
    vector = np.zeros(size, dtype=np.float32)
    vector[index] = 1.0
    return vector


class TestL2Normalize:
    def test_normalizes_to_unit_length(self) -> None:
        vector = np.array([3.0, 4.0], dtype=np.float32)
        normalized = l2_normalize(vector)
        assert pytest.approx(np.linalg.norm(normalized), rel=1e-5) == 1.0

    def test_zero_vector_unchanged(self) -> None:
        vector = np.zeros(4, dtype=np.float32)
        assert np.array_equal(l2_normalize(vector), vector)


class TestCosineSimilarity:
    def test_identical_vectors_score_one(self) -> None:
        vector = _unit_vector(0)
        assert pytest.approx(cosine_similarity(vector, vector), rel=1e-5) == 1.0

    def test_orthogonal_vectors_score_zero(self) -> None:
        a = _unit_vector(0)
        b = _unit_vector(1)
        assert pytest.approx(cosine_similarity(a, b), rel=1e-5) == 0.0


class TestSelectSpeaker:
    def test_picks_best_above_threshold(self) -> None:
        query = _unit_vector(0)
        speakers = {
            "miguel": _unit_vector(0),
            "ana": _unit_vector(1),
        }
        result = select_speaker(query, speakers, threshold=0.5, margin=0.05)
        assert result.person == "miguel"
        assert result.is_known is True
        assert result.score > 0.99

    def test_returns_unknown_below_threshold(self) -> None:
        query = _unit_vector(0)
        speakers = {"miguel": _unit_vector(2)}
        result = select_speaker(query, speakers, threshold=0.9, margin=0.05)
        assert result.person == UNKNOWN_SPEAKER
        assert result.is_known is False

    def test_returns_unknown_when_margin_too_small(self) -> None:
        query = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float32)
        speakers = {
            "miguel": np.array([1.0, 0.9, 0.0, 0.0], dtype=np.float32),
            "ana": np.array([0.9, 1.0, 0.0, 0.0], dtype=np.float32),
        }
        result = select_speaker(query, speakers, threshold=0.5, margin=0.2)
        assert result.person == UNKNOWN_SPEAKER
        assert result.is_known is False
        assert result.second_best_person is not None

    def test_empty_speakers_returns_unknown(self) -> None:
        result = select_speaker(_unit_vector(0), {}, threshold=0.6)
        assert result.person == UNKNOWN_SPEAKER
        assert result.score == 0.0


class TestValidateProfiles:
    def test_valid_example_passes(self) -> None:
        data = {
            "version": 1,
            "model": "wespeaker_en_voxceleb_resnet34.onnx",
            "embedding_dim": 3,
            "threshold": 0.6,
            "margin": 0.05,
            "speakers": {
                "miguel": {"centroid": [1.0, 0.0, 0.0], "clip_count": 10},
            },
        }
        assert validate_profiles(data) == []

    def test_missing_speakers_fails(self) -> None:
        data = {
            "version": 1,
            "model": "test.onnx",
            "embedding_dim": 3,
            "threshold": 0.6,
            "margin": 0.05,
            "speakers": {},
        }
        errors = validate_profiles(data)
        assert any("at least one" in error for error in errors)

    def test_centroid_dim_mismatch_fails(self) -> None:
        data = {
            "version": 1,
            "model": "test.onnx",
            "embedding_dim": 4,
            "threshold": 0.6,
            "margin": 0.05,
            "speakers": {
                "miguel": {"centroid": [1.0, 0.0], "clip_count": 5},
            },
        }
        errors = validate_profiles(data)
        assert any("centroid length" in error for error in errors)

    def test_example_file_in_repo_is_valid(self) -> None:
        example = SPEAKER_ID_DIR / "speaker_profiles.example.json"
        if not example.is_file():
            pytest.skip("example file not present")
        with example.open(encoding="utf-8") as handle:
            data = json.load(handle)
        assert validate_profiles(data) == []
