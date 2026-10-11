"""Opaque session tokens. Only the SHA-256 lives in SQLite."""

from __future__ import annotations

import hashlib
import secrets


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)
