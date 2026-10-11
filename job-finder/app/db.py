"""SQLAlchemy 2 engine. SQLite WAL is applied on each connection."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def sqlite_file_path(url: str) -> Path | None:
    """Return the filesystem path for a SQLite URL, or None if not a file DB."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return None
    database = parsed.database
    if not database or database == ":memory:":
        return None
    return Path(database)


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:")


def create_engine_from_settings(settings: Settings) -> Engine:
    url = settings.job_finder_database_url
    connect_args: dict[str, object] = {}
    if _is_sqlite(url):
        connect_args = {"check_same_thread": False, "timeout": 5}

    engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
    )

    if _is_sqlite(url):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ping_database(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
