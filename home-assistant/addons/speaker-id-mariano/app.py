"""FastAPI service for speaker identification (Home Assistant add-on)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from recognizer import IdentificationResult, SpeakerRecognizer, UNKNOWN_SPEAKER

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("speaker-id-mariano")

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/share/speaker-id/wespeaker_en_voxceleb_resnet34.onnx"))
PROFILES_PATH = Path(os.getenv("PROFILES_PATH", "/share/speaker-id/speaker_profiles.json"))
THRESHOLD = float(os.getenv("THRESHOLD", "0.6"))
MARGIN = float(os.getenv("MARGIN", "0.05"))
NUM_THREADS = int(os.getenv("NUM_THREADS", "1"))
ALLOWED_PREFIXES = (
    "/share/assist_pipeline",
    "/share/speaker-id",
    "/tmp",
)

app = FastAPI(title="Speaker ID Mariano", version="1.0.0")
recognizer = SpeakerRecognizer(
    model_path=MODEL_PATH,
    profiles_path=PROFILES_PATH,
    threshold=THRESHOLD,
    margin=MARGIN,
    num_threads=NUM_THREADS,
)


class IdentifyPathRequest(BaseModel):
    path: str = Field(..., description="Absolute path to a WAV file under /share")


class IdentifyResponse(BaseModel):
    person: str
    score: float
    is_known: bool
    second_best_person: str | None = None
    second_best_score: float | None = None


def _to_response(result: IdentificationResult) -> IdentifyResponse:
    return IdentifyResponse(
        person=result.person,
        score=round(result.score, 4),
        is_known=result.is_known,
        second_best_person=result.second_best_person,
        second_best_score=(
            round(result.second_best_score, 4)
            if result.second_best_score is not None
            else None
        ),
    )


def _validate_share_path(path_str: str) -> Path:
    try:
        resolved = Path(path_str).resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid path: {exc}") from exc

    allowed = any(str(resolved).startswith(prefix) for prefix in ALLOWED_PREFIXES)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Path not allowed (must be under {ALLOWED_PREFIXES})",
        )
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {resolved}")
    if resolved.suffix.lower() != ".wav":
        raise HTTPException(status_code=400, detail="Only .wav files are supported")

    return resolved


@app.on_event("startup")
def startup() -> None:
    recognizer.load()
    logger.info("Speaker ID Mariano ready — speakers: %s", recognizer.speaker_names)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", **recognizer.health()}


@app.post("/reload")
def reload_profiles() -> dict:
    try:
        recognizer.reload_profiles()
    except Exception as exc:
        logger.exception("Failed to reload profiles")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "reloaded", "speakers": recognizer.speaker_names}


@app.post("/identify", response_model=IdentifyResponse)
def identify_by_path(request: IdentifyPathRequest) -> IdentifyResponse:
    wav_path = _validate_share_path(request.path)
    try:
        result = recognizer.identify_file(wav_path)
    except Exception as exc:
        logger.exception("Identification failed for %s", wav_path)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_response(result)


@app.post("/identify/upload", response_model=IdentifyResponse)
async def identify_upload(file: UploadFile = File(...)) -> IdentifyResponse:
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Upload must be a .wav file")

    temp_path = Path("/tmp") / f"upload_{file.filename}"
    content = await file.read()
    temp_path.write_bytes(content)

    try:
        result = recognizer.identify_file(temp_path)
    except Exception as exc:
        logger.exception("Upload identification failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)

    return _to_response(result)


@app.get("/")
def root() -> dict:
    return {
        "service": "speaker-id-mariano",
        "unknown_label": UNKNOWN_SPEAKER,
        "endpoints": ["/health", "/identify", "/identify/upload", "/reload"],
    }
