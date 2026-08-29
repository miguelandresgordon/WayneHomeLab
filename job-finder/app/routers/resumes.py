"""Resume (CV) upload and download. PDF only, per-user storage, authz on every read."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.deps import csrf_from_form, get_db, require_csrf, require_user
from app.models import Resume, SearchProfile, User
from app.services.resumes import (
    new_storage_key,
    read_and_validate_pdf,
    resume_file_path,
    schedule_resume_file_delete,
    sha256_hex,
    write_resume_file,
)

router = APIRouter(tags=["resumes"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _serialize(resume: Resume) -> dict[str, object]:
    return {
        "id": resume.id,
        "search_profile_id": resume.search_profile_id,
        "original_filename": resume.original_filename,
        "mime_type": resume.mime_type,
        "size_bytes": resume.size_bytes,
        "is_default": resume.is_default,
        "created_at": resume.created_at.isoformat(),
    }


def _get_owned(db: Session, user: User, resume_id: int) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    return resume


@router.get("/api/v1/resumes")
def list_resumes(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    resumes = db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id))
    return [_serialize(r) for r in resumes]


@router.post("/api/v1/resumes", status_code=201)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
    search_profile_id: int | None = Form(default=None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    # multipart/form-data cannot carry the CSRF header reliably in every client,
    # so the token travels as a form field and is checked explicitly (see deps.require_csrf).
    csrf_from_form(csrf_token, request)
    settings = _settings(request)

    if search_profile_id is not None:
        profile = db.get(SearchProfile, search_profile_id)
        if profile is None or profile.user_id != user.id:
            raise HTTPException(status_code=404, detail="search profile not found")

    data = await read_and_validate_pdf(file, settings)
    storage_key = new_storage_key(user.id)

    resume = Resume(
        user_id=user.id,
        search_profile_id=search_profile_id,
        original_filename=(file.filename or "resume.pdf")[:255],
        mime_type="application/pdf",
        size_bytes=len(data),
        sha256=sha256_hex(data),
        storage_key=storage_key,
        is_default=False,
    )
    db.add(resume)
    db.flush()
    write_resume_file(db, settings, storage_key, data)
    return _serialize(resume)


@router.delete("/api/v1/resumes/{resume_id}", status_code=204)
def delete_resume(
    resume_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> None:
    resume = _get_owned(db, user, resume_id)
    schedule_resume_file_delete(db, _settings(request), resume.storage_key)
    db.delete(resume)


@router.post("/api/v1/resumes/{resume_id}/default")
def set_default_resume(
    resume_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict[str, object]:
    resume = _get_owned(db, user, resume_id)
    others = db.scalars(select(Resume).where(Resume.user_id == user.id, Resume.id != resume.id))
    for other in others:
        other.is_default = False
    resume.is_default = True
    db.flush()
    return _serialize(resume)


@router.get("/api/v1/resumes/{resume_id}/file")
def download_resume(
    resume_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    resume = _get_owned(db, user, resume_id)
    path = resume_file_path(_settings(request), resume.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file missing")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=resume.original_filename,
        headers={"Cache-Control": "no-store"},
    )
