"""SQLite URL parsing and WAL pragma."""

from pathlib import Path

from sqlalchemy import text

from app.db import sqlite_file_path


def test_sqlite_file_path_absolute() -> None:
    assert sqlite_file_path("sqlite:////data/jobfinder.db") == Path("/data/jobfinder.db")


def test_sqlite_file_path_relative() -> None:
    assert sqlite_file_path("sqlite:///./data/jobfinder.db") == Path("./data/jobfinder.db")


def test_sqlite_file_path_memory() -> None:
    assert sqlite_file_path("sqlite:///:memory:") is None


def test_journal_mode_is_wal(client) -> None:
    engine = client.app.state.engine
    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert str(mode).lower() == "wal"
