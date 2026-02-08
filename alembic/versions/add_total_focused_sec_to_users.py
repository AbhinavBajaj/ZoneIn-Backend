"""add total_focused_sec to users

Revision ID: add_total_focused_sec
Revises: add_activity_public
Create Date: 2026-02-07 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_total_focused_sec"
down_revision: Union[str, Sequence[str], None] = "add_activity_public"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("total_focused_sec", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "total_focused_sec")
