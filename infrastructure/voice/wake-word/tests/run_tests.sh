#!/usr/bin/env bash
# run_tests.sh — TDD test runner for wake-word infrastructure
#
# Usage: ./infrastructure/voice/wake-word/tests/run_tests.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
WAKE_WORD_DIR="$REPO_ROOT/infrastructure/voice/wake-word"

log() { printf '[wake-word-tests] %s\n' "$*"; }
fail() { log "FAIL: $*"; exit 1; }

log "Running Python config tests..."
if ! python3 -c "import pytest, yaml" 2>/dev/null; then
  log "Installing test deps (pytest, pyyaml)..."
  python3 -m pip install --quiet pytest pyyaml
fi

python3 -m pytest \
  "$SCRIPT_DIR/test_wake_word_config.py" \
  "$SCRIPT_DIR/test_pad_personal_samples.py" \
  "$SCRIPT_DIR/test_keep_personal_and_windows.py" \
  -v

log "Running BATS shell tests..."
if ! command -v bats >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    log "Installing bats-core..."
    brew install bats-core
  else
    fail "bats not found and brew unavailable"
  fi
fi

bats "$SCRIPT_DIR/test_shell_scripts.bats"

log "All wake-word tests passed."
