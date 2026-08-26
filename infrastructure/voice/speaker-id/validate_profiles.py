#!/usr/bin/env python3
"""Validate speaker_profiles.json exported from the Colab enrollment notebook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL_KEYS = {
    "version",
    "model",
    "embedding_dim",
    "threshold",
    "margin",
    "speakers",
}

REQUIRED_SPEAKER_KEYS = {"centroid", "clip_count"}


def validate_profiles(data: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty if valid)."""
    errors: list[str] = []

    missing = REQUIRED_TOP_LEVEL_KEYS - set(data.keys())
    if missing:
        errors.append(f"Missing top-level keys: {sorted(missing)}")

    version = data.get("version")
    if version is not None and not isinstance(version, int):
        errors.append("'version' must be an integer")

    embedding_dim = data.get("embedding_dim")
    if embedding_dim is not None:
        if not isinstance(embedding_dim, int) or embedding_dim <= 0:
            errors.append("'embedding_dim' must be a positive integer")

    threshold = data.get("threshold")
    if threshold is not None:
        if not isinstance(threshold, (int, float)) or not 0.0 <= float(threshold) <= 1.0:
            errors.append("'threshold' must be a float between 0 and 1")

    margin = data.get("margin")
    if margin is not None:
        if not isinstance(margin, (int, float)) or not 0.0 <= float(margin) <= 1.0:
            errors.append("'margin' must be a float between 0 and 1")

    speakers = data.get("speakers")
    if speakers is None:
        return errors

    if not isinstance(speakers, dict):
        errors.append("'speakers' must be an object")
        return errors

    if not speakers:
        errors.append("'speakers' must contain at least one enrolled person")

    for name, profile in speakers.items():
        if not isinstance(name, str) or not name.strip():
            errors.append("Speaker names must be non-empty strings")
            continue

        if not isinstance(profile, dict):
            errors.append(f"Speaker '{name}' profile must be an object")
            continue

        missing_speaker = REQUIRED_SPEAKER_KEYS - set(profile.keys())
        if missing_speaker:
            errors.append(f"Speaker '{name}' missing keys: {sorted(missing_speaker)}")
            continue

        clip_count = profile.get("clip_count")
        if not isinstance(clip_count, int) or clip_count <= 0:
            errors.append(f"Speaker '{name}' clip_count must be a positive integer")

        centroid = profile.get("centroid")
        if not isinstance(centroid, list) or not centroid:
            errors.append(f"Speaker '{name}' centroid must be a non-empty list")
            continue

        if embedding_dim is not None and len(centroid) != embedding_dim:
            errors.append(
                f"Speaker '{name}' centroid length {len(centroid)} "
                f"!= embedding_dim {embedding_dim}"
            )

        if not all(isinstance(value, (int, float)) for value in centroid):
            errors.append(f"Speaker '{name}' centroid must contain only numbers")

    return errors


def load_profiles(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profiles_file",
        type=Path,
        help="Path to speaker_profiles.json",
    )
    args = parser.parse_args()

    if not args.profiles_file.is_file():
        print(f"ERROR: file not found: {args.profiles_file}", file=sys.stderr)
        return 1

    try:
        data = load_profiles(args.profiles_file)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        return 1

    errors = validate_profiles(data)
    if errors:
        print("INVALID speaker_profiles.json:")
        for error in errors:
            print(f"  - {error}")
        return 1

    speaker_count = len(data["speakers"])
    print(f"OK: {speaker_count} speaker(s), dim={data['embedding_dim']}, threshold={data['threshold']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
