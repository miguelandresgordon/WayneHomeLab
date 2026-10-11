"""Resume file storage: opaque paths on disk, one PDF per row.

Files are never named or pathed from user input. Only the SHA-256 and the
generated storage_key are persisted; the original filename is kept solely
for display and download headers.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.config import Settings

PDF_MAGIC = b"%PDF-"
_READ_CHUNK_BYTES = 64 * 1024
_PENDING_WRITES = "resume_pending_writes"
_PENDING_DELETES = "resume_pending_deletes"


def resumes_root(settings: Settings) -> Path:
    return Path(settings.job_finder_resumes_dir)


def ensure_resumes_root(settings: Settings) -> None:
    resumes_root(settings).mkdir(parents=True, exist_ok=True)


def register_resume_session_hooks() -> None:
    @event.listens_for(Session, "after_commit")
    def _delete_resume_files_after_commit(session: Session) -> None:
        for path in session.info.pop(_PENDING_DELETES, []):
            Path(path).unlink(missing_ok=True)
        session.info.pop(_PENDING_WRITES, None)

    @event.listens_for(Session, "after_rollback")
    def _cleanup_resume_files_after_rollback(session: Session) -> None:
        for path in session.info.pop(_PENDING_WRITES, []):
            Path(path).unlink(missing_ok=True)
        session.info.pop(_PENDING_DELETES, None)


def new_storage_key(user_id: int) -> str:
    return f"{user_id}/{uuid.uuid4().hex}.pdf"


def safe_resume_file_path(settings: Settings, storage_key: str) -> Path:
    if not storage_key or storage_key.startswith("/") or ".." in storage_key.split("/"):
        raise HTTPException(status_code=400, detail="invalid storage key")
    root = resumes_root(settings).resolve()
    path = (root / storage_key).resolve()
    if path != root and root not in path.parents:
        raise HTTPException(status_code=400, detail="invalid storage key")
    return path


def resume_file_path(settings: Settings, storage_key: str) -> Path:
    return safe_resume_file_path(settings, storage_key)


async def read_and_validate_pdf(upload: UploadFile, settings: Settings) -> bytes:
    chunks: list[bytes] = []
    total = 0
    max_bytes = settings.job_finder_resume_max_bytes
    while True:
        chunk = await upload.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="file too large")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(status_code=415, detail="only pdf files are accepted")
    return data


def write_resume_file(session: Session, settings: Settings, storage_key: str, data: bytes) -> None:
    path = safe_resume_file_path(settings, storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    session.info.setdefault(_PENDING_WRITES, []).append(str(path))


def schedule_resume_file_delete(session: Session, settings: Settings, storage_key: str) -> None:
    path = safe_resume_file_path(settings, storage_key)
    session.info.setdefault(_PENDING_DELETES, []).append(str(path))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
