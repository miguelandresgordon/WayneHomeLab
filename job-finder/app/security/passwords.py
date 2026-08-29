"""Argon2id password hashing."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import Settings


def _hasher(settings: Settings) -> PasswordHasher:
    return PasswordHasher(
        time_cost=settings.job_finder_argon2_time_cost,
        memory_cost=settings.job_finder_argon2_memory_cost,
        parallelism=settings.job_finder_argon2_parallelism,
    )


def hash_password(password: str, settings: Settings) -> str:
    return _hasher(settings).hash(password)


def verify_password(password_hash: str, password: str, settings: Settings) -> bool:
    try:
        return _hasher(settings).verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
