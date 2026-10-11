"""User identity/contact profile. One row per user, minimal PII."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_csrf, require_user
from app.models import User, UserProfile

router = APIRouter(tags=["profile"])


class ProfileBody(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=200)
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=4000)


def _serialize(profile: UserProfile | None) -> dict[str, object]:
    if profile is None:
        return {
            "full_name": None,
            "phone": None,
            "location": None,
            "linkedin_url": None,
            "portfolio_url": None,
            "summary": None,
        }
    return {
        "full_name": profile.full_name,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "summary": profile.summary,
    }


def _get_own_profile(db: Session, user: User) -> UserProfile | None:
    return db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))


@router.get("/api/v1/profile")
def get_profile(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _serialize(_get_own_profile(db, user))


@router.put("/api/v1/profile")
def put_profile(
    body: ProfileBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict[str, object]:
    profile = _get_own_profile(db, user)
    if profile is None:
        profile = UserProfile(user_id=user.id, full_name=body.full_name)
        db.add(profile)
    profile.full_name = body.full_name
    profile.phone = body.phone
    profile.location = body.location
    profile.linkedin_url = body.linkedin_url
    profile.portfolio_url = body.portfolio_url
    profile.summary = body.summary
    db.flush()
    return _serialize(profile)
