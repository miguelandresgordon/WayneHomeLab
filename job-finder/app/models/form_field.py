"""Inventoried field plus mapping. Never stores ATS passwords or hidden tokens."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.form_page import FormPage


class FormField(Base):
    __tablename__ = "form_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("form_pages.id", ondelete="CASCADE"), index=True)
    local_id: Mapped[str] = mapped_column(String(80))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    element: Mapped[str] = mapped_column(String(40))
    type: Mapped[str] = mapped_column(String(40))
    signals_json: Mapped[dict] = mapped_column(JSON, default=dict)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_action: Mapped[str] = mapped_column(String(20))
    review_reason: Mapped[str | None] = mapped_column(String(80), default=None)
    profile_key: Mapped[str | None] = mapped_column(String(80), default=None)
    mapped_value: Mapped[str | None] = mapped_column(Text, default=None)
    doc_ref_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    explanation: Mapped[str] = mapped_column(String(500), default="")
    sensitivity: Mapped[str] = mapped_column(String(20), default="normal")
    fill_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    already_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    page: Mapped["FormPage"] = relationship(back_populates="fields")
