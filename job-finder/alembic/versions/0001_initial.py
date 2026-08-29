"""Initial Alembic revision.

No domain tables yet. Later phases add User, profiles, and applications.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-27
"""

from typing import Sequence, Union

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
