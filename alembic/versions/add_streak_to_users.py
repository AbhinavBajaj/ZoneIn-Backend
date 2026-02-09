"""add streak_count and last_activity_date to users

Revision ID: add_streak
Revises: add_avatar_url
Create Date: 2026-02-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_streak"
down_revision: Union[str, Sequence[str], None] = "add_avatar_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("streak_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("last_activity_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_activity_date")
    op.drop_column("users", "streak_count")
