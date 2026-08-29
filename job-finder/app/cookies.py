"""Cookie helpers for session and CSRF."""

from __future__ import annotations

from datetime import timedelta

from fastapi import Request, Response

from app.config import Settings
from app.deps import CSRF_COOKIE, SESSION_COOKIE
from app.security.tokens import new_csrf_token


def _cookie_kwargs(settings: Settings) -> dict[str, object]:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.job_finder_cookie_secure,
        "path": "/",
        "max_age": int(timedelta(hours=settings.job_finder_session_hours).total_seconds()),
    }


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    kwargs = _cookie_kwargs(settings)
    response.set_cookie(SESSION_COOKIE, token, **kwargs)  # type: ignore[arg-type]


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        samesite="lax",
        secure=settings.job_finder_cookie_secure,
    )


def ensure_csrf_cookie(request: Request, response: Response, settings: Settings) -> str:
    existing = request.cookies.get(CSRF_COOKIE)
    if existing:
        return existing
    token = new_csrf_token()
    kwargs = _cookie_kwargs(settings)
    kwargs["httponly"] = False
    response.set_cookie(CSRF_COOKIE, token, **kwargs)  # type: ignore[arg-type]
    return token


def set_csrf_cookie(response: Response, token: str, settings: Settings) -> None:
    kwargs = _cookie_kwargs(settings)
    kwargs["httponly"] = False
    response.set_cookie(CSRF_COOKIE, token, **kwargs)  # type: ignore[arg-type]
