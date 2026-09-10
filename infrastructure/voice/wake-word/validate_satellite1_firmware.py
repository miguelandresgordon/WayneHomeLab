#!/usr/bin/env python3
"""Validate Satellite1 ESPHome YAML for ESPHome 2026.x Device Builder.

ESPHome 2026.8 treats voice_assistant as a singleton: `id: !extend va` is
parsed as a literal id and fails with "The character '!' cannot be used".
`!extend` remains valid on list components (e.g. select).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WAKE_WORD_DIR = Path(__file__).resolve().parent
DEFAULT_FILES = (
    WAKE_WORD_DIR / "esphome" / "satellite1-c7ffe4.yaml",
    WAKE_WORD_DIR / "satellite1_mariano_overlay.yaml",
)


def _first_key_value(block_lines: list[str], key: str) -> str | None:
    prefix = f"{key}:"
    for raw in block_lines:
        stripped = raw.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if stripped.startswith(prefix):
            return stripped.split(":", 1)[1].strip()
    return None


def _top_level_block(text: str, name: str) -> list[str]:
    lines = text.splitlines()
    collected: list[str] = []
    in_block = False
    for line in lines:
        if line.startswith(f"{name}:") and (len(line) == len(name) + 1 or line[len(name) + 1 : len(name) + 2] in ("", " ")):
            in_block = True
            continue
        if in_block:
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            collected.append(line)
    return collected


def validate_firmware_yaml(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    label = str(path)

    if "REPLACE_BY_32_BIT_RANDOM_KEY" in text and "api:" in text:
        errors.append(f"{label}: placeholder API key still present")
    api = _top_level_block(text, "api")
    if path.name == "satellite1-c7ffe4.yaml":
        if not api:
            errors.append(f"{label}: missing api encryption block (OTA needs Noise PSK)")
        else:
            api_blob = "\n".join(api)
            if "encryption:" not in api_blob:
                errors.append(f"{label}: api.encryption missing")
            if "!secret api_encryption_key" not in api_blob:
                errors.append(f"{label}: api.encryption.key must be !secret api_encryption_key")
    if "id: mariano" not in text:
        errors.append(f"{label}: missing micro_wake_word id mariano")
    if "mariano.esphome.json" not in text:
        errors.append(f"{label}: missing mariano.esphome.json model URL")

    va = _top_level_block(text, "voice_assistant")
    if not va:
        errors.append(f"{label}: missing voice_assistant block")
        return errors

    va_id = _first_key_value(va, "id")
    if va_id is None:
        errors.append(f"{label}: voice_assistant missing id")
    elif va_id.startswith("!"):
        errors.append(
            f"{label}: voice_assistant id cannot use {va_id!r} "
            "(ESPHome 2026 singleton — use `id: va`, not !extend)"
        )
    elif va_id != "va":
        errors.append(f"{label}: voice_assistant id must be 'va' (FPH), got {va_id!r}")

    va_blob = "\n".join(va)
    for needle in ("noise_suppression_level:", "auto_gain:", "volume_multiplier:", "on_stt_end:"):
        if needle not in va_blob:
            errors.append(f"{label}: voice_assistant missing {needle[:-1]}")
    if "esphome.satellite1_stt_end" not in va_blob:
        errors.append(f"{label}: voice_assistant missing esphome.satellite1_stt_end")

    sel = _top_level_block(text, "select")
    if sel:
        sel_id = _first_key_value(sel, "id")
        if sel_id != "!extend mww_sensitivity_select":
            errors.append(
                f"{label}: select must extend mww_sensitivity_select, got {sel_id!r}"
            )
        if "id(mariano)" not in "\n".join(sel):
            errors.append(f"{label}: select lambda must call id(mariano)")
        if "set_probability_cutoff(250)" not in "\n".join(sel):
            errors.append(f"{label}: select lambda missing Slightly=250 cutoff")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="YAML files (default: repo firmware + overlay)")
    args = parser.parse_args()
    files = args.files or list(DEFAULT_FILES)
    errors: list[str] = []
    for path in files:
        if not path.is_file():
            errors.append(f"missing file: {path}")
            continue
        errors.extend(validate_firmware_yaml(path))
    if errors:
        print("Satellite1 firmware YAML invalid:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Satellite1 firmware YAML OK (ESPHome 2026 singleton + select !extend)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
