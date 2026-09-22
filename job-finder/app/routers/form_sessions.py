"""Form-session API used by the Safari extension (Bearer) and the web UI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_db, require_csrf, require_user
from app.models import User
from app.services.form_sessions import (
    analyze_session,
    complete_session,
    get_or_create_session,
    get_own_session,
    record_fill_result,
    serialize_session,
)
from app.services.mapping import SCHEMA_VERSION

router = APIRouter(tags=["form-sessions"])


class SessionCreateBody(BaseModel):
    origin: str = Field(min_length=3, max_length=500)
    tab_key: str = Field(min_length=1, max_length=80)
    apply_url: str | None = Field(default=None, max_length=2000)


class InventoryPage(BaseModel):
    origin: str = Field(min_length=3, max_length=500)
    path: str = Field(default="", max_length=2000)
    title: str = Field(default="", max_length=500)


class InventoryField(BaseModel):
    local_id: str = Field(min_length=1, max_length=80)
    element: str = Field(default="input", max_length=40)
    type: str = Field(min_length=1, max_length=40)
    signals: dict[str, Any] = Field(default_factory=dict)
    required: bool = False
    allowed_action: str | None = None
    review_reason: str | None = None
    options: list[dict[str, Any]] | None = None
    multiple: bool = False


class AnalyzeBody(BaseModel):
    schema_version: int
    page: InventoryPage
    fields: list[InventoryField] = Field(default_factory=list)
    blocked_frames: int = 0


class FillResultItem(BaseModel):
    local_id: str = Field(min_length=1, max_length=80)
    ok: bool
    reason: str | None = Field(default=None, max_length=80)


class FillResultBody(BaseModel):
    results: list[FillResultItem] = Field(default_factory=list)


def _session_or_404(db: Session, user: User, session_id: int):
    session = get_own_session(db, user, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="not found")
    return session


@router.post("/api/v1/form-sessions")
def create_form_session(
    body: SessionCreateBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _: None = Depends(require_csrf),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key = (idempotency_key or "").strip() or None
    session, created = get_or_create_session(
        db,
        user,
        request.app.state.settings,
        origin=body.origin.rstrip("/"),
        tab_key=body.tab_key,
        apply_url=body.apply_url,
        idempotency_key=key,
    )
    payload = serialize_session(session)
    payload["created"] = created
    return payload


@router.get("/api/v1/form-sessions/{session_id}")
def get_form_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> dict[str, Any]:
    return serialize_session(_session_or_404(db, user, session_id))


@router.post("/api/v1/form-sessions/{session_id}/analyze")
def analyze_form_session(
    session_id: int,
    body: AnalyzeBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _: None = Depends(require_csrf),
) -> dict[str, Any]:
    limiter = request.app.state.analyze_limiter
    client_host = request.client.host if request.client else "unknown"
    if not limiter.allow(f"{user.id}:{client_host}"):
        raise HTTPException(status_code=429, detail="too many analyze requests")
    if body.schema_version != SCHEMA_VERSION:
        raise HTTPException(status_code=422, detail="unsupported schema_version")
    session = _session_or_404(db, user, session_id)
    if session.state != "open":
        raise HTTPException(status_code=409, detail="session closed")
    inventory = body.model_dump()
    try:
        return analyze_session(db, user, session, inventory)
    except ValueError as exc:
        if str(exc) == "origin_changed":
            raise HTTPException(
                status_code=409,
                detail="origin_changed",
            ) from exc
        raise


@router.post("/api/v1/form-sessions/{session_id}/fill-result")
def fill_result(
    session_id: int,
    body: FillResultBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _: None = Depends(require_csrf),
) -> dict[str, Any]:
    session = _session_or_404(db, user, session_id)
    return record_fill_result(db, session, [item.model_dump() for item in body.results])


@router.post("/api/v1/form-sessions/{session_id}/complete")
def complete_form_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _: None = Depends(require_csrf),
) -> dict[str, Any]:
    session = _session_or_404(db, user, session_id)
    return complete_session(db, session)
