"""Alembic env loads and current head matches the latest revision."""

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_head_is_latest() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert heads == ["0003_profiles_resumes_answers"]
