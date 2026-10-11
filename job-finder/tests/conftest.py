"""Shared FastAPI test client with two bootstrapped users."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

USER_A_EMAIL = "user-a@local.test"
USER_A_PASSWORD = "test-pass-a-ok"
USER_B_EMAIL = "user-b@local.test"
USER_B_PASSWORD = "test-pass-b-ok"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "jobfinder.db"
    resumes_dir = tmp_path / "resumes"
    monkeypatch.setenv("JOB_FINDER_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JOB_FINDER_RESUMES_DIR", str(resumes_dir))
    monkeypatch.setenv("JOB_FINDER_VERSION", "0.1.0-test")
    monkeypatch.setenv("JOB_FINDER_SECRET_KEY", "test-secret-not-for-prod")
    monkeypatch.setenv("JOB_FINDER_USER_A_EMAIL", USER_A_EMAIL)
    monkeypatch.setenv("JOB_FINDER_USER_A_PASSWORD", USER_A_PASSWORD)
    monkeypatch.setenv("JOB_FINDER_USER_B_EMAIL", USER_B_EMAIL)
    monkeypatch.setenv("JOB_FINDER_USER_B_PASSWORD", USER_B_PASSWORD)
    monkeypatch.setenv("JOB_FINDER_ARGON2_TIME_COST", "1")
    monkeypatch.setenv("JOB_FINDER_ARGON2_MEMORY_COST", "8192")
    monkeypatch.setenv("JOB_FINDER_LOGIN_RATE_LIMIT", "20")
    get_settings.cache_clear()
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    settings = get_settings()
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client
    get_settings.cache_clear()


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.get("/api/v1/auth/csrf").json()["csrf"]
    return {"X-CSRF-Token": token}


def login(client: TestClient, email: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers=csrf_headers(client),
    )
