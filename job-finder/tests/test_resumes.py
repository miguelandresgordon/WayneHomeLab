"""Resume upload, download, default flag, and cross-user isolation."""

from pathlib import Path

from tests.conftest import (
    USER_A_EMAIL,
    USER_A_PASSWORD,
    USER_B_EMAIL,
    USER_B_PASSWORD,
    csrf_headers,
    login,
)

MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"


def _csrf_form_token(client) -> str:
    client.get("/api/v1/auth/csrf")
    return client.cookies.get("jf_csrf")


def _upload(client, filename: str = "cv.pdf", data: bytes = MINIMAL_PDF):
    return client.post(
        "/api/v1/resumes",
        files={"file": (filename, data, "application/pdf")},
        data={"csrf_token": _csrf_form_token(client)},
    )


def test_upload_list_download_delete_resume(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    uploaded = _upload(client)
    assert uploaded.status_code == 201
    resume_id = uploaded.json()["id"]
    assert uploaded.json()["mime_type"] == "application/pdf"

    listed = client.get("/api/v1/resumes")
    assert len(listed.json()) == 1

    downloaded = client.get(f"/api/v1/resumes/{resume_id}/file")
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF-")
    assert downloaded.headers["cache-control"] == "no-store"

    deleted = client.delete(f"/api/v1/resumes/{resume_id}", headers=csrf_headers(client))
    assert deleted.status_code == 204
    assert client.get("/api/v1/resumes").json() == []


def test_upload_rejects_non_pdf(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    response = _upload(client, filename="cv.txt", data=b"not a pdf")
    assert response.status_code == 415


def test_upload_requires_csrf(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    response = client.post(
        "/api/v1/resumes",
        files={"file": ("cv.pdf", MINIMAL_PDF, "application/pdf")},
        data={"csrf_token": "wrong"},
    )
    assert response.status_code == 403


def test_set_default_resume(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    first = _upload(client, filename="a.pdf").json()
    second = _upload(client, filename="b.pdf").json()

    client.post(f"/api/v1/resumes/{second['id']}/default", headers=csrf_headers(client))
    listed = {r["id"]: r["is_default"] for r in client.get("/api/v1/resumes").json()}
    assert listed[first["id"]] is False
    assert listed[second["id"]] is True


def test_resume_isolated_per_user(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    resume = _upload(client).json()
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))

    login(client, USER_B_EMAIL, USER_B_PASSWORD)
    forbidden = client.get(f"/api/v1/resumes/{resume['id']}/file")
    assert forbidden.status_code == 404

    forbidden_delete = client.delete(f"/api/v1/resumes/{resume['id']}", headers=csrf_headers(client))
    assert forbidden_delete.status_code == 404


def test_delete_removes_resume_file(client, tmp_path: Path) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    resume = _upload(client).json()
    stored = list((tmp_path / "resumes").glob("*/*.pdf"))
    assert len(stored) == 1

    deleted = client.delete(f"/api/v1/resumes/{resume['id']}", headers=csrf_headers(client))
    assert deleted.status_code == 204
    assert list((tmp_path / "resumes").glob("*/*.pdf")) == []


def test_safe_resume_file_path_rejects_traversal(tmp_path: Path, monkeypatch) -> None:
    from fastapi import HTTPException
    import pytest

    from app.config import get_settings
    from app.services.resumes import safe_resume_file_path

    monkeypatch.setenv("JOB_FINDER_RESUMES_DIR", str(tmp_path))
    get_settings.cache_clear()
    settings = get_settings()

    with pytest.raises(HTTPException) as exc_info:
        safe_resume_file_path(settings, "../../etc/passwd")
    assert exc_info.value.status_code == 400
    get_settings.cache_clear()
