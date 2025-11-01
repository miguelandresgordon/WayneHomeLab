# Charo Core Service

Voice Controller core service for Proyecto Charo.

## Development

```bash
# Install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## TDD Workflow

See [.claude/CLAUDE.md](../../.claude/CLAUDE.md) for TDD methodology.
