"""add activity_public to session_reports

Revision ID: add_activity_public
Revises: add_username_to_users
Create Date: 2026-02-07 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_activity_public"
down_revision: Union[str, Sequence[str], None] = "add_focus_pct_half"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_reports",
        sa.Column("activity_public", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("session_reports", "activity_public")
