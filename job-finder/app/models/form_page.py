"""One URL observed inside a form session (multipage / SPA)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.form_field import FormField
    from app.models.form_session import FormSession


class FormPage(Base):
    __tablename__ = "form_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("form_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str] = mapped_column(String(500), default="")
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["FormSession"] = relationship(back_populates="pages")
    fields: Mapped[list["FormField"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
    )
