"""Employment preferences, one-to-one with a search profile."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.search_profile import SearchProfile


class EmploymentPreference(Base):
    __tablename__ = "employment_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_profile_id: Mapped[int] = mapped_column(
        ForeignKey("search_profiles.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    desired_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    seniority_level: Mapped[str | None] = mapped_column(String(60), default=None)
    work_mode: Mapped[str | None] = mapped_column(String(20), default=None)
    employment_type: Mapped[str | None] = mapped_column(String(20), default=None)
    salary_min: Mapped[int | None] = mapped_column(Integer, default=None)
    salary_max: Mapped[int | None] = mapped_column(Integer, default=None)
    salary_currency: Mapped[str | None] = mapped_column(String(10), default=None)
    availability: Mapped[str | None] = mapped_column(String(60), default=None)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, default=None)
    work_authorization: Mapped[str | None] = mapped_column(String(60), default=None)
    requires_sponsorship: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    willing_to_travel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    search_profile: Mapped["SearchProfile"] = relationship(back_populates="preferences")
