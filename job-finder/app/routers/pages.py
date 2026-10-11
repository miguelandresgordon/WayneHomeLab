"""Server-side pages: login form and home."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.cookies import (
    clear_session_cookie,
    set_csrf_cookie,
    set_session_cookie,
)
from app.deps import CSRF_COOKIE, SESSION_COOKIE, csrf_from_form, get_db, get_optional_user
from app.models import User
from app.security.tokens import new_csrf_token
from app.services.auth import authenticate, create_auth_session, revoke_auth_session

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["pages"])

ERROR_MESSAGES = {
    "invalid": "Correo o contraseña incorrectos.",
    "rate": "Demasiados intentos. Espera unos minutos.",
    "csrf": "La sesión de seguridad expiró. Vuelve a intentar.",
}


def _html(
    request: Request,
    name: str,
    context: dict[str, object],
) -> HTMLResponse:
    settings = request.app.state.settings
    token = request.cookies.get(CSRF_COOKIE) or new_csrf_token()
    context = {**context, "csrf_token": token}
    response = templates.TemplateResponse(request=request, name=name, context=context)
    if CSRF_COOKIE not in request.cookies:
        set_csrf_cookie(response, token, settings)
    return response


@router.get("/", include_in_schema=False)
def home(
    request: Request,
    user: User | None = Depends(get_optional_user),
) -> HTMLResponse:
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    return _html(
        request,
        "home.html",
        {"title": "Job Finder", "user": user},
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    user: User | None = Depends(get_optional_user),
) -> HTMLResponse:
    if user is not None:
        return RedirectResponse(url="/", status_code=302)
    error_key = request.query_params.get("error")
    return _html(
        request,
        "login.html",
        {
            "title": "Job Finder",
            "error": ERROR_MESSAGES.get(error_key or "", None),
        },
    )


@router.post("/login", include_in_schema=False)
def login_form_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        csrf_from_form(csrf_token, request)
    except HTTPException:
        return RedirectResponse(url="/login?error=csrf", status_code=303)
    limiter = request.app.state.login_limiter
    key = request.client.host if request.client else "unknown"
    if not limiter.allow(key):
        return RedirectResponse(url="/login?error=rate", status_code=303)
    settings = request.app.state.settings
    user = authenticate(db, email, password, settings)
    if user is None:
        return RedirectResponse(url="/login?error=invalid", status_code=303)
    raw = create_auth_session(db, user, settings)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, raw, settings)
    set_csrf_cookie(response, new_csrf_token(), settings)
    return response


@router.post("/logout", include_in_schema=False)
def logout_form(
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    csrf_from_form(csrf_token, request)
    settings = request.app.state.settings
    revoke_auth_session(db, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response, settings)
    return response
