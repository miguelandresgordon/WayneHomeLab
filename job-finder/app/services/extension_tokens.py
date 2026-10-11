"""Create, list and revoke Safari extension API tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ExtensionDevice, User
from app.security.tokens import hash_token, new_session_token


def serialize_device(device: ExtensionDevice, *, include_token: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": device.id,
        "name": device.name,
        "expires_at": device.expires_at.isoformat(),
        "revoked_at": device.revoked_at.isoformat() if device.revoked_at else None,
        "created_at": device.created_at.isoformat() if device.created_at else None,
    }
    if include_token is not None:
        payload["token"] = include_token
    return payload


def create_extension_token(db: Session, user: User, settings: Settings, name: str) -> tuple[ExtensionDevice, str]:
    raw = new_session_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.job_finder_extension_token_days)
    device = ExtensionDevice(
        user_id=user.id,
        name=name.strip() or "Safari",
        token_hash=hash_token(raw),
        expires_at=expires,
    )
    db.add(device)
    db.flush()
    return device, raw


def list_extension_tokens(db: Session, user: User) -> list[ExtensionDevice]:
    return list(
        db.scalars(
            select(ExtensionDevice)
            .where(ExtensionDevice.user_id == user.id)
            .order_by(ExtensionDevice.created_at.desc())
        ).all()
    )


def revoke_extension_token(db: Session, user: User, token_id: int) -> ExtensionDevice | None:
    device = db.scalar(
        select(ExtensionDevice).where(
            ExtensionDevice.id == token_id,
            ExtensionDevice.user_id == user.id,
        )
    )
    if device is None:
        return None
    if device.revoked_at is None:
        device.revoked_at = datetime.now(timezone.utc)
        db.flush()
    return device
