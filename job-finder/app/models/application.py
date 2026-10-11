"""Candidacy record created from a form session. Status is user-driven."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.form_session import FormSession
    from app.models.user import User


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    form_session_id: Mapped[int] = mapped_column(
        ForeignKey("form_sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    apply_url: Mapped[str | None] = mapped_column(String(2000), default=None)
    ats_origin: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="applications")
    form_session: Mapped["FormSession"] = relationship(back_populates="application")
