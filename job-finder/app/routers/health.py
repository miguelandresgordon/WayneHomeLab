"""Liveness and database ping. No PII."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine

from app.db import ping_database

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
def health(request: Request) -> JSONResponse:
    engine: Engine = request.app.state.engine
    version: str = request.app.state.version
    try:
        ping_database(engine)
        db_status = "ok"
        http_status = 200
        status = "ok"
    except Exception:
        db_status = "error"
        http_status = 503
        status = "degraded"

    return JSONResponse(
        status_code=http_status,
        content={
            "status": status,
            "db": db_status,
            "version": version,
        },
    )
