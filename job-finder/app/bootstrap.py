"""Create the two household users once, from environment variables."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.security.passwords import hash_password

logger = logging.getLogger("job-finder")


def bootstrap_users(engine: Engine, settings: Settings) -> None:
    pairs = (
        (settings.job_finder_user_a_email, settings.job_finder_user_a_password),
        (settings.job_finder_user_b_email, settings.job_finder_user_b_password),
    )
    with Session(engine) as db:
        for email, password in pairs:
            if not email or not password:
                continue
            normalized = email.strip().lower()
            exists = db.scalar(select(User).where(User.email == normalized))
            if exists is not None:
                continue
            db.add(
                User(
                    email=normalized,
                    password_hash=hash_password(password, settings),
                    is_active=True,
                )
            )
            logger.info("Bootstrapped user %s", normalized)
        db.commit()
