"""Short-lived form-fill session scoped to one user, origin and tab."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.form_page import FormPage
    from app.models.user import User


class FormSession(Base):
    __tablename__ = "form_sessions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_form_sessions_user_idempotency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(500), index=True)
    tab_key: Mapped[str] = mapped_column(String(80), index=True)
    apply_url: Mapped[str | None] = mapped_column(String(2000), default=None)
    search_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("search_profiles.id", ondelete="SET NULL"),
        default=None,
    )
    resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        default=None,
    )
    state: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="form_sessions")
    pages: Mapped[list["FormPage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    application: Mapped["Application | None"] = relationship(
        back_populates="form_session",
        uselist=False,
        cascade="all, delete-orphan",
    )
