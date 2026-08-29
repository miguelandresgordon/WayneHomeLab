"""FastAPI application factory. Single uvicorn worker in production."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.bootstrap import bootstrap_users
from app.config import Settings, get_settings
from app.db import create_engine_from_settings, session_factory, sqlite_file_path
from app.routers import auth, health, pages, profile, resumes, reusable_answers, search_profiles, users
from app.security.rate_limit import LoginLimiter
from app.services.resumes import ensure_resumes_root, register_resume_session_hooks

logger = logging.getLogger("job-finder")


def _ensure_sqlite_parent(database_url: str) -> None:
    path = sqlite_file_path(database_url)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    bootstrap_users(app.state.engine, app.state.settings)
    yield
    engine = app.state.engine
    engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    _ensure_sqlite_parent(settings.job_finder_database_url)
    ensure_resumes_root(settings)
    register_resume_session_hooks()
    engine = create_engine_from_settings(settings)
    logger.info("Job Finder %s starting", settings.job_finder_version)

    app = FastAPI(
        title="Job Finder",
        version=settings.job_finder_version,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory(engine)
    app.state.version = settings.job_finder_version
    app.state.login_limiter = LoginLimiter(
        max_attempts=settings.job_finder_login_rate_limit,
        window_seconds=settings.job_finder_login_rate_window_seconds,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(profile.router)
    app.include_router(search_profiles.router)
    app.include_router(resumes.router)
    app.include_router(reusable_answers.router)
    app.include_router(pages.router)
    return app
