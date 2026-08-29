"""Named search profiles and their employment preferences. Owner-scoped."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_csrf, require_user
from app.models import EmploymentPreference, SearchProfile, User

router = APIRouter(tags=["search-profiles"])


class SearchProfileBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_default: bool = False
    is_active: bool = True


class PreferencesBody(BaseModel):
    """Partial update: only fields present in the JSON body are changed."""

    desired_roles: list[str] | None = None
    locations: list[str] | None = None
    seniority_level: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    availability: str | None = None
    notice_period_days: int | None = None
    work_authorization: str | None = None
    requires_sponsorship: bool | None = None
    willing_to_relocate: bool | None = None
    willing_to_travel: bool | None = None


def _serialize(profile: SearchProfile) -> dict[str, object]:
    return {
        "id": profile.id,
        "name": profile.name,
        "is_default": profile.is_default,
        "is_active": profile.is_active,
    }


def _serialize_preferences(prefs: EmploymentPreference | None) -> dict[str, object] | None:
    if prefs is None:
        return None
    return {
        "desired_roles": prefs.desired_roles,
        "locations": prefs.locations,
        "seniority_level": prefs.seniority_level,
        "work_mode": prefs.work_mode,
        "employment_type": prefs.employment_type,
        "salary_min": prefs.salary_min,
        "salary_max": prefs.salary_max,
        "salary_currency": prefs.salary_currency,
        "availability": prefs.availability,
        "notice_period_days": prefs.notice_period_days,
        "work_authorization": prefs.work_authorization,
        "requires_sponsorship": prefs.requires_sponsorship,
        "willing_to_relocate": prefs.willing_to_relocate,
        "willing_to_travel": prefs.willing_to_travel,
    }


def _get_owned(db: Session, user: User, profile_id: int) -> SearchProfile:
    profile = db.get(SearchProfile, profile_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    return profile


def _clear_other_defaults(db: Session, user: User, keep_id: int) -> None:
    others = db.scalars(
        select(SearchProfile).where(SearchProfile.user_id == user.id, SearchProfile.id != keep_id)
    )
    for other in others:
        other.is_default = False


def _check_unique_name(db: Session, user: User, name: str, exclude_id: int | None) -> None:
    query = select(SearchProfile).where(SearchProfile.user_id == user.id, SearchProfile.name == name)
    if exclude_id is not None:
        query = query.where(SearchProfile.id != exclude_id)
    if db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail="a profile with that name already exists")


@router.get("/api/v1/search-profiles")
def list_search_profiles(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    profiles = db.scalars(
        select(SearchProfile).where(SearchProfile.user_id == user.id).order_by(SearchProfile.id)
    )
    return [_serialize(p) for p in profiles]


@router.post("/api/v1/search-profiles", status_code=201)
def create_search_profile(
    body: SearchProfileBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict[str, object]:
    _check_unique_name(db, user, body.name, exclude_id=None)
    profile = SearchProfile(
        user_id=user.id,
        name=body.name,
        is_default=body.is_default,
        is_active=body.is_active,
    )
    db.add(profile)
    db.flush()
    if body.is_default:
        _clear_other_defaults(db, user, profile.id)
    return _serialize(profile)


@router.get("/api/v1/search-profiles/{profile_id}")
def get_search_profile(
    profile_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = _get_owned(db, user, profile_id)
    return {**_serialize(profile), "preferences": _serialize_preferences(profile.preferences)}


@router.put("/api/v1/search-profiles/{profile_id}")
def update_search_profile(
    profile_id: int,
    body: SearchProfileBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict[str, object]:
    profile = _get_owned(db, user, profile_id)
    _check_unique_name(db, user, body.name, exclude_id=profile.id)
    profile.name = body.name
    profile.is_active = body.is_active
    profile.is_default = body.is_default
    if body.is_default:
        _clear_other_defaults(db, user, profile.id)
    return _serialize(profile)


@router.delete("/api/v1/search-profiles/{profile_id}", status_code=204)
def delete_search_profile(
    profile_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> None:
    profile = _get_owned(db, user, profile_id)
    db.delete(profile)


@router.put("/api/v1/search-profiles/{profile_id}/preferences")
def put_preferences(
    profile_id: int,
    body: PreferencesBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict[str, object]:
    profile = _get_owned(db, user, profile_id)
    prefs = profile.preferences
    if prefs is None:
        prefs = EmploymentPreference(search_profile_id=profile.id)
        db.add(prefs)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.flush()
    serialized = _serialize_preferences(prefs)
    assert serialized is not None
    return serialized
