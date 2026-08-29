"""FastAPI dependencies: DB session, current user, CSRF."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AuthSession, User
from app.security.tokens import hash_token

SESSION_COOKIE = "jf_session"
CSRF_COOKIE = "jf_csrf"
CSRF_HEADER = "x-csrf-token"


def get_db(request: Request) -> Generator[Session, None, None]:
    factory = request.app.state.session_factory
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    token_hash = hash_token(raw)
    now = datetime.now(timezone.utc)
    auth_session = db.scalar(
        select(AuthSession)
        .options(selectinload(AuthSession.user))
        .where(
            AuthSession.token_hash == token_hash,
            AuthSession.expires_at > now,
        )
    )
    if auth_session is None:
        return None
    user = auth_session.user
    if not user.is_active:
        return None
    return user


def require_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE)
    if not cookie:
        raise HTTPException(status_code=403, detail="csrf missing")
    submitted = request.headers.get(CSRF_HEADER)
    if submitted is None and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            # Form token is checked in the route via Form(); header-only here for JSON.
            return
    if submitted != cookie:
        raise HTTPException(status_code=403, detail="csrf invalid")


def csrf_from_form(csrf_token: str | None, request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE)
    if not cookie or not csrf_token or csrf_token != cookie:
        raise HTTPException(status_code=403, detail="csrf invalid")
