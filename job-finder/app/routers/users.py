"""User endpoints. All reads are scoped to the authenticated owner."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_user
from app.models import User

router = APIRouter(tags=["users"])


def _public_user(user: User) -> dict[str, object]:
    return {"id": user.id, "email": user.email}


@router.get("/api/v1/me")
def me(user: User = Depends(require_user)) -> dict[str, object]:
    return _public_user(user)


@router.get("/api/v1/users/{user_id}")
def get_user(
    user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    found = db.get(User, user_id)
    if found is None or not found.is_active:
        raise HTTPException(status_code=404, detail="not found")
    return _public_user(found)
