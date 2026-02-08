"""add published_at to session_reports

Revision ID: add_published_at
Revises: add_total_focused_sec
Create Date: 2026-02-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_published_at"
down_revision: Union[str, Sequence[str], None] = "add_total_focused_sec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_reports",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_reports", "published_at")
