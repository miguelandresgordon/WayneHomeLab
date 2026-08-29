"""Reusable answers the user explicitly saves for autofill review. Never auto-generated."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_csrf, require_user
from app.models import ReusableAnswer, User

router = APIRouter(tags=["reusable-answers"])


class ReusableAnswerBody(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    locale: str = Field(default="es", min_length=2, max_length=10)
    text: str = Field(min_length=1, max_length=8000)


def _serialize(answer: ReusableAnswer) -> dict[str, object]:
    return {
        "id": answer.id,
        "key": answer.key,
        "locale": answer.locale,
        "text": answer.text,
        "source": answer.source,
    }


def _get_owned(db: Session, user: User, answer_id: int) -> ReusableAnswer:
    answer = db.get(ReusableAnswer, answer_id)
    if answer is None or answer.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    return answer


@router.get("/api/v1/reusable-answers")
def list_answers(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    answers = db.scalars(
        select(ReusableAnswer).where(ReusableAnswer.user_id == user.id).order_by(ReusableAnswer.id)
    )
    return [_serialize(a) for a in answers]


@router.post("/api/v1/reusable-answers", status_code=201)
def create_answer(
    body: ReusableAnswerBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict[str, object]:
    exists = db.scalar(
        select(ReusableAnswer).where(
            ReusableAnswer.user_id == user.id,
            ReusableAnswer.key == body.key,
            ReusableAnswer.locale == body.locale,
        )
    )
    if exists is not None:
        raise HTTPException(status_code=409, detail="answer already exists for that key/locale")
    answer = ReusableAnswer(user_id=user.id, key=body.key, locale=body.locale, text=body.text)
    db.add(answer)
    db.flush()
    return _serialize(answer)


@router.put("/api/v1/reusable-answers/{answer_id}")
def update_answer(
    answer_id: int,
    body: ReusableAnswerBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict[str, object]:
    answer = _get_owned(db, user, answer_id)
    duplicate = db.scalar(
        select(ReusableAnswer).where(
            ReusableAnswer.user_id == user.id,
            ReusableAnswer.key == body.key,
            ReusableAnswer.locale == body.locale,
            ReusableAnswer.id != answer.id,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="answer already exists for that key/locale")
    answer.key = body.key
    answer.locale = body.locale
    answer.text = body.text
    db.flush()
    return _serialize(answer)


@router.delete("/api/v1/reusable-answers/{answer_id}", status_code=204)
def delete_answer(
    answer_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> None:
    answer = _get_owned(db, user, answer_id)
    db.delete(answer)
