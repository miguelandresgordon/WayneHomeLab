#!/usr/bin/env bash
# run_all.sh — Single entrypoint for the whole WayneHomeLab test suite.
#
#   ./tests/run_all.sh            # everything (pytest + BATS + firmware YAML validator)
#   ./tests/run_all.sh -k radio   # extra args are forwarded to pytest
#
# Uses the repo .venv when present (pytest, hassil, yamllint, rapidfuzz).
# Out of scope: job-finder/ and weather-intelligence/ (own suites).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() { printf '[run_all] %s\n' "$*"; }

pick_python() {
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
  else
    command -v python3
  fi
}

PY="$(pick_python)"
PY_BIN="$(dirname "$PY")"
export PATH="$PY_BIN:$PATH"

ensure_python_deps() {
  if ! "$PY" -c "import pytest, yaml, hassil, yamllint, rapidfuzz" 2>/dev/null; then
    log "Installing test deps into $(dirname "$PY")..."
    "$PY" -m pip install --quiet pytest pyyaml hassil yamllint rapidfuzz
  fi
}

run_firmware_validator() {
  log "Satellite1 firmware YAML validator..."
  "$PY" infrastructure/voice/wake-word/validate_satellite1_firmware.py
}

run_pytest() {
  log "pytest..."
  "$PY" -m pytest -q -p no:cacheprovider \
    tests \
    infrastructure/voice/wake-word/tests \
    home-assistant/addons/speaker-id-mariano/tests \
    "$@"
}

run_bats() {
  if ! command -v bats >/dev/null 2>&1; then
    log "bats not installed — skipping shell BATS tests (brew install bats-core)"
    return 0
  fi
  log "BATS shell tests..."
  local suites=()
  while IFS= read -r f; do suites+=("$f"); done < <(git ls-files '*.bats' | grep -v -E '^(job-finder|weather-intelligence)/')
  if [[ ${#suites[@]} -gt 0 ]]; then
    bats "${suites[@]}"
  fi
}

main() {
  ensure_python_deps
  run_firmware_validator
  run_pytest "$@"
  run_bats
  log "✅ All suites passed"
}

main "$@"
