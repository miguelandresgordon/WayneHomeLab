"""Profiles, search profiles, employment preferences, resumes, reusable answers.

Revision ID: 0003_profiles_resumes_answers
Revises: 0002_users_sessions
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_profiles_resumes_answers"
down_revision: Union[str, Sequence[str], None] = "0002_users_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("portfolio_url", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "search_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_search_profiles_user_name"),
    )
    op.create_index("ix_search_profiles_user_id", "search_profiles", ["user_id"], unique=False)

    op.create_table(
        "employment_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("search_profile_id", sa.Integer(), nullable=False),
        sa.Column("desired_roles", sa.JSON(), nullable=False),
        sa.Column("locations", sa.JSON(), nullable=False),
        sa.Column("seniority_level", sa.String(length=60), nullable=True),
        sa.Column("work_mode", sa.String(length=20), nullable=True),
        sa.Column("employment_type", sa.String(length=20), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=10), nullable=True),
        sa.Column("availability", sa.String(length=60), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column("work_authorization", sa.String(length=60), nullable=True),
        sa.Column("requires_sponsorship", sa.Boolean(), nullable=False),
        sa.Column("willing_to_relocate", sa.Boolean(), nullable=False),
        sa.Column("willing_to_travel", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["search_profile_id"], ["search_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_employment_preferences_search_profile_id",
        "employment_preferences",
        ["search_profile_id"],
        unique=True,
    )

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("search_profile_id", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_profile_id"], ["search_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"], unique=False)
    op.create_index("ix_resumes_search_profile_id", "resumes", ["search_profile_id"], unique=False)
    op.create_index("ix_resumes_sha256", "resumes", ["sha256"], unique=False)
    op.create_index("ix_resumes_storage_key", "resumes", ["storage_key"], unique=True)

    op.create_table(
        "reusable_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", "locale", name="uq_reusable_answers_user_key_locale"),
    )
    op.create_index("ix_reusable_answers_user_id", "reusable_answers", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reusable_answers_user_id", table_name="reusable_answers")
    op.drop_table("reusable_answers")

    op.drop_index("ix_resumes_storage_key", table_name="resumes")
    op.drop_index("ix_resumes_sha256", table_name="resumes")
    op.drop_index("ix_resumes_search_profile_id", table_name="resumes")
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")

    op.drop_index("ix_employment_preferences_search_profile_id", table_name="employment_preferences")
    op.drop_table("employment_preferences")

    op.drop_index("ix_search_profiles_user_id", table_name="search_profiles")
    op.drop_table("search_profiles")

    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")
