"""Form session lifecycle: reuse by (user, origin, tab), analyze, fill-result."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.models import (
    Application,
    FormField,
    FormPage,
    FormSession,
    Resume,
    ReusableAnswer,
    SearchProfile,
    User,
    UserProfile,
)
from app.services.mapping import SCHEMA_VERSION, map_inventory


def _now() -> datetime:
    return datetime.now(timezone.utc)


def serialize_session(session: FormSession) -> dict[str, Any]:
    application = session.application
    return {
        "id": session.id,
        "origin": session.origin,
        "tab_key": session.tab_key,
        "apply_url": session.apply_url,
        "state": session.state,
        "expires_at": session.expires_at.isoformat(),
        "application_id": application.id if application else None,
        "application_status": application.status if application else None,
    }


def serialize_mapping(row: FormField) -> dict[str, Any]:
    return {
        "local_id": row.local_id,
        "fingerprint": row.fingerprint,
        "profile_key": row.profile_key,
        "value": row.mapped_value,
        "doc_ref": row.doc_ref_json,
        "confidence": row.confidence,
        "explanation": row.explanation,
        "requires_review": row.allowed_action != "fill",
        "sensitivity": row.sensitivity,
        "allowed_action": row.allowed_action,
        "review_reason": row.review_reason,
        "already_resolved": row.already_resolved,
        "fill_status": row.fill_status,
        "type": row.type,
        "signals": row.signals_json,
    }


def get_own_session(db: Session, user: User, session_id: int) -> FormSession | None:
    return db.scalar(
        select(FormSession)
        .options(
            selectinload(FormSession.application),
            selectinload(FormSession.pages).selectinload(FormPage.fields),
        )
        .where(FormSession.id == session_id, FormSession.user_id == user.id)
    )


def _default_search_profile_id(db: Session, user: User) -> int | None:
    profile = db.scalar(
        select(SearchProfile).where(
            SearchProfile.user_id == user.id,
            SearchProfile.is_default.is_(True),
        )
    )
    if profile is not None:
        return profile.id
    profile = db.scalar(select(SearchProfile).where(SearchProfile.user_id == user.id))
    return profile.id if profile else None


def _default_resume(db: Session, user: User, search_profile_id: int | None) -> Resume | None:
    if search_profile_id is not None:
        linked = db.scalar(
            select(Resume).where(
                Resume.user_id == user.id,
                Resume.search_profile_id == search_profile_id,
                Resume.is_default.is_(True),
            )
        )
        if linked is not None:
            return linked
    return db.scalar(
        select(Resume).where(Resume.user_id == user.id, Resume.is_default.is_(True))
    ) or db.scalar(select(Resume).where(Resume.user_id == user.id))


def get_or_create_session(
    db: Session,
    user: User,
    settings: Settings,
    *,
    origin: str,
    tab_key: str,
    apply_url: str | None,
    idempotency_key: str | None,
) -> tuple[FormSession, bool]:
    now = _now()
    if idempotency_key:
        existing_idemp = db.scalar(
            select(FormSession)
            .options(selectinload(FormSession.application))
            .where(
                FormSession.user_id == user.id,
                FormSession.idempotency_key == idempotency_key,
            )
        )
        if existing_idemp is not None:
            return existing_idemp, False

    existing = db.scalar(
        select(FormSession)
        .options(selectinload(FormSession.application))
        .where(
            FormSession.user_id == user.id,
            FormSession.origin == origin,
            FormSession.tab_key == tab_key,
            FormSession.state == "open",
            FormSession.expires_at > now,
        )
        .order_by(FormSession.created_at.desc())
    )
    if existing is not None:
        if apply_url and not existing.apply_url:
            existing.apply_url = apply_url
            if existing.application and not existing.application.apply_url:
                existing.application.apply_url = apply_url
            db.flush()
        return existing, False

    search_profile_id = _default_search_profile_id(db, user)
    resume = _default_resume(db, user, search_profile_id)
    session = FormSession(
        user_id=user.id,
        origin=origin,
        tab_key=tab_key,
        apply_url=apply_url,
        search_profile_id=search_profile_id,
        resume_id=resume.id if resume else None,
        state="open",
        idempotency_key=idempotency_key,
        expires_at=now + timedelta(hours=settings.job_finder_form_session_hours),
    )
    db.add(session)
    db.flush()
    db.add(
        Application(
            user_id=user.id,
            form_session_id=session.id,
            apply_url=apply_url,
            ats_origin=origin,
            status="in_progress",
            resume_id=session.resume_id,
        )
    )
    db.flush()
    db.refresh(session, attribute_names=["application"])
    return session, True


def _mapping_context(db: Session, user: User, session: FormSession) -> dict[str, Any]:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    search_profile = None
    if session.search_profile_id is not None:
        search_profile = db.scalar(
            select(SearchProfile)
            .options(selectinload(SearchProfile.preferences))
            .where(
                SearchProfile.id == session.search_profile_id,
                SearchProfile.user_id == user.id,
            )
        )
    resume = None
    if session.resume_id is not None:
        resume = db.scalar(
            select(Resume).where(Resume.id == session.resume_id, Resume.user_id == user.id)
        )
    answers = list(
        db.scalars(select(ReusableAnswer).where(ReusableAnswer.user_id == user.id)).all()
    )
    preference = {}
    if search_profile and search_profile.preferences is not None:
        prefs = search_profile.preferences
        preference = {
            "desired_roles": prefs.desired_roles or [],
            "locations": prefs.locations or [],
            "work_mode": prefs.work_mode,
            "availability": prefs.availability,
            "salary_min": prefs.salary_min,
            "willing_to_relocate": prefs.willing_to_relocate,
            "willing_to_travel": prefs.willing_to_travel,
            "requires_sponsorship": prefs.requires_sponsorship,
        }
    return {
        "email": user.email,
        "profile": {
            "full_name": profile.full_name if profile else None,
            "phone": profile.phone if profile else None,
            "location": profile.location if profile else None,
            "linkedin_url": profile.linkedin_url if profile else None,
            "portfolio_url": profile.portfolio_url if profile else None,
            "summary": profile.summary if profile else None,
        },
        "preference": preference,
        "resume": (
            {"id": resume.id, "original_filename": resume.original_filename}
            if resume
            else None
        ),
        "answers": [{"key": item.key, "text": item.text} for item in answers],
    }


def resolved_fingerprints_for(db: Session, session: FormSession) -> set[str]:
    fingerprints: set[str] = set()
    page_ids = [page.id for page in session.pages]
    if not page_ids:
        pages = list(db.scalars(select(FormPage).where(FormPage.session_id == session.id)).all())
        page_ids = [page.id for page in pages]
    if not page_ids:
        return fingerprints
    rows = db.scalars(
        select(FormField).where(
            FormField.page_id.in_(page_ids),
            FormField.fill_status == "applied",
        )
    ).all()
    for row in rows:
        fingerprints.add(row.fingerprint)
    return fingerprints


def analyze_session(
    db: Session,
    user: User,
    session: FormSession,
    inventory: dict[str, Any],
) -> dict[str, Any]:
    page_meta = inventory.get("page") or {}
    origin = str(page_meta.get("origin") or "")
    if origin and origin != session.origin:
        raise ValueError("origin_changed")
    path = str(page_meta.get("path") or "")
    url = f"{session.origin}{path}"
    page = FormPage(
        session_id=session.id,
        url=url,
        title=str(page_meta.get("title") or ""),
    )
    db.add(page)
    db.flush()

    context = _mapping_context(db, user, session)
    resolved = resolved_fingerprints_for(db, session)
    mappings = map_inventory(list(inventory.get("fields") or []), context, resolved)
    rows: list[FormField] = []
    for mapping in mappings:
        fill_status = "skipped" if mapping["already_resolved"] else "pending"
        if mapping["allowed_action"] == "never":
            fill_status = "never"
        row = FormField(
            page_id=page.id,
            local_id=str(mapping["local_id"]),
            fingerprint=mapping["fingerprint"],
            element=str(mapping["element"]),
            type=str(mapping["type"]),
            signals_json=mapping["signals"],
            required=bool(mapping["required"]),
            allowed_action=mapping["allowed_action"],
            review_reason=mapping["review_reason"],
            profile_key=mapping["profile_key"],
            mapped_value=mapping["value"],
            doc_ref_json=mapping["doc_ref"],
            confidence=mapping["confidence"],
            explanation=mapping["explanation"],
            sensitivity=mapping["sensitivity"],
            fill_status=fill_status,
            already_resolved=bool(mapping["already_resolved"]),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return {
        "schema_version": SCHEMA_VERSION,
        "session": serialize_session(session),
        "page_id": page.id,
        "blocked_frames": inventory.get("blocked_frames") or 0,
        "mappings": [serialize_mapping(row) for row in rows],
    }


def record_fill_result(
    db: Session,
    session: FormSession,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_page = db.scalar(
        select(FormPage)
        .where(FormPage.session_id == session.id)
        .order_by(FormPage.seen_at.desc(), FormPage.id.desc())
    )
    if latest_page is None:
        return {"updated": 0, "results": []}
    by_local = {
        field.local_id: field
        for field in db.scalars(select(FormField).where(FormField.page_id == latest_page.id)).all()
    }
    updated = []
    for item in results:
        local_id = str(item.get("local_id") or "")
        field = by_local.get(local_id)
        if field is None:
            continue
        if field.allowed_action == "never":
            field.fill_status = "never"
        elif item.get("ok") is True:
            field.fill_status = "applied"
        else:
            field.fill_status = "failed"
            reason = item.get("reason")
            if reason:
                field.review_reason = str(reason)[:80]
        updated.append(serialize_mapping(field))
    db.flush()
    return {"updated": len(updated), "results": updated}


def complete_session(db: Session, session: FormSession) -> dict[str, Any]:
    session.state = "complete"
    if session.application is not None:
        session.application.status = "applied"
    db.flush()
    return serialize_session(session)
