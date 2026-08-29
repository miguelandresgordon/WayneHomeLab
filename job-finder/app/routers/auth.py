"""Authentication HTTP API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import Settings
from app.cookies import (
    clear_session_cookie,
    set_csrf_cookie,
    set_session_cookie,
)
from app.deps import CSRF_COOKIE, SESSION_COOKIE, get_db, require_csrf
from app.security.tokens import new_csrf_token
from app.services.auth import authenticate, create_auth_session, revoke_auth_session

router = APIRouter(tags=["auth"])


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _client_key(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


def _enforce_login_rate(request: Request) -> None:
    limiter = request.app.state.login_limiter
    if not limiter.allow(_client_key(request)):
        raise HTTPException(status_code=429, detail="too many login attempts")


@router.get("/api/v1/auth/csrf")
def issue_csrf(request: Request) -> JSONResponse:
    settings = _settings(request)
    token = request.cookies.get(CSRF_COOKIE) or new_csrf_token()
    response = JSONResponse({"csrf": token})
    if CSRF_COOKIE not in request.cookies:
        set_csrf_cookie(response, token, settings)
    return response


@router.post("/api/v1/auth/login")
def login_json(
    body: LoginBody,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    _enforce_login_rate(request)
    settings = _settings(request)
    user = authenticate(db, body.email, body.password, settings)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    raw = create_auth_session(db, user, settings)
    response = JSONResponse({"id": user.id, "email": user.email})
    set_session_cookie(response, raw, settings)
    set_csrf_cookie(response, new_csrf_token(), settings)
    return response


@router.post("/api/v1/auth/logout")
def logout_json(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    settings = _settings(request)
    revoke_auth_session(db, request.cookies.get(SESSION_COOKIE))
    response = JSONResponse({"ok": True})
    clear_session_cookie(response, settings)
    return response
