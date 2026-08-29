"""Login session lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AuthSession, User
from app.security.passwords import verify_password
from app.security.tokens import hash_token, new_session_token


def authenticate(db: Session, email: str, password: str, settings: Settings) -> User | None:
    normalized = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized))
    if user is None or not user.is_active:
        return None
    if not verify_password(user.password_hash, password, settings):
        return None
    return user


def create_auth_session(db: Session, user: User, settings: Settings) -> str:
    raw = new_session_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.job_finder_session_hours)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=expires,
        )
    )
    db.flush()
    return raw


def revoke_auth_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    token_hash = hash_token(raw_token)
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if session is not None:
        db.delete(session)
