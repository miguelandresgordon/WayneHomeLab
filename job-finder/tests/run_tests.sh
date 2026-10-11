#!/usr/bin/env bash
# Run Job Finder unit tests (no Docker required).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

if ! python3 -c "import pytest, fastapi, sqlalchemy, alembic" 2>/dev/null; then
  echo "Installing test dependencies..."
  python3 -m pip install --quiet -r requirements-dev.txt
fi

python3 -m pytest tests/ -v
