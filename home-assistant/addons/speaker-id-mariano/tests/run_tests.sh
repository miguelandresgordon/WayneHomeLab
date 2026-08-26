#!/usr/bin/env bash
# Run speaker-id-mariano unit tests (pure logic, no sherpa-onnx required).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if ! python3 -c "import numpy" 2>/dev/null; then
  echo "Installing test dependencies..."
  pip3 install -q numpy pytest
fi

python3 -m pytest tests/ -v
python3 "${SCRIPT_DIR}/../../../infrastructure/voice/speaker-id/validate_profiles.py" \
  "${SCRIPT_DIR}/../../../infrastructure/voice/speaker-id/speaker_profiles.example.json"
