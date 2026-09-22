"""Form sessions, extension devices, applications.

Revision ID: 0004_form_sessions
Revises: 0003_profiles_resumes_answers
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_form_sessions"
down_revision: Union[str, Sequence[str], None] = "0003_profiles_resumes_answers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extension_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extension_devices_user_id", "extension_devices", ["user_id"], unique=False)
    op.create_index("ix_extension_devices_token_hash", "extension_devices", ["token_hash"], unique=True)
    op.create_index("ix_extension_devices_expires_at", "extension_devices", ["expires_at"], unique=False)

    op.create_table(
        "form_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=500), nullable=False),
        sa.Column("tab_key", sa.String(length=80), nullable=False),
        sa.Column("apply_url", sa.String(length=2000), nullable=True),
        sa.Column("search_profile_id", sa.Integer(), nullable=True),
        sa.Column("resume_id", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_profile_id"], ["search_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_form_sessions_user_idempotency"),
    )
    op.create_index("ix_form_sessions_user_id", "form_sessions", ["user_id"], unique=False)
    op.create_index("ix_form_sessions_origin", "form_sessions", ["origin"], unique=False)
    op.create_index("ix_form_sessions_tab_key", "form_sessions", ["tab_key"], unique=False)
    op.create_index("ix_form_sessions_expires_at", "form_sessions", ["expires_at"], unique=False)

    op.create_table(
        "form_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["form_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_form_pages_session_id", "form_pages", ["session_id"], unique=False)

    op.create_table(
        "form_fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("local_id", sa.String(length=80), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("element", sa.String(length=40), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("signals_json", sa.JSON(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("allowed_action", sa.String(length=20), nullable=False),
        sa.Column("review_reason", sa.String(length=80), nullable=True),
        sa.Column("profile_key", sa.String(length=80), nullable=True),
        sa.Column("mapped_value", sa.Text(), nullable=True),
        sa.Column("doc_ref_json", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.String(length=500), nullable=False),
        sa.Column("sensitivity", sa.String(length=20), nullable=False),
        sa.Column("fill_status", sa.String(length=20), nullable=False),
        sa.Column("already_resolved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["form_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_form_fields_page_id", "form_fields", ["page_id"], unique=False)
    op.create_index("ix_form_fields_fingerprint", "form_fields", ["fingerprint"], unique=False)

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("form_session_id", sa.Integer(), nullable=False),
        sa.Column("apply_url", sa.String(length=2000), nullable=True),
        sa.Column("ats_origin", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["form_session_id"], ["form_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"], unique=False)
    op.create_index("ix_applications_form_session_id", "applications", ["form_session_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_applications_form_session_id", table_name="applications")
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_table("applications")

    op.drop_index("ix_form_fields_fingerprint", table_name="form_fields")
    op.drop_index("ix_form_fields_page_id", table_name="form_fields")
    op.drop_table("form_fields")

    op.drop_index("ix_form_pages_session_id", table_name="form_pages")
    op.drop_table("form_pages")

    op.drop_index("ix_form_sessions_expires_at", table_name="form_sessions")
    op.drop_index("ix_form_sessions_tab_key", table_name="form_sessions")
    op.drop_index("ix_form_sessions_origin", table_name="form_sessions")
    op.drop_index("ix_form_sessions_user_id", table_name="form_sessions")
    op.drop_table("form_sessions")

    op.drop_index("ix_extension_devices_expires_at", table_name="extension_devices")
    op.drop_index("ix_extension_devices_token_hash", table_name="extension_devices")
    op.drop_index("ix_extension_devices_user_id", table_name="extension_devices")
    op.drop_table("extension_devices")
