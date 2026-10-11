"""Named search profiles. A user may keep several; only one is the default."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.employment_preference import EmploymentPreference
    from app.models.user import User


class SearchProfile(Base):
    __tablename__ = "search_profiles"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_search_profiles_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="search_profiles")
    preferences: Mapped["EmploymentPreference | None"] = relationship(
        back_populates="search_profile",
        uselist=False,
        cascade="all, delete-orphan",
    )
