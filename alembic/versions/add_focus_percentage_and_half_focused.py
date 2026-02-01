"""add focus_percentage and half_focused_segments_json to session_reports

Revision ID: add_focus_pct_half
Revises: add_max_zone_in_score_to_users
Create Date: 2026-01-31 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_focus_pct_half"
down_revision: Union[str, Sequence[str], None] = "add_max_zone_in_score_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_reports", sa.Column("focus_percentage", sa.Float(), nullable=True))
    op.add_column("session_reports", sa.Column("half_focused_segments_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("session_reports", "half_focused_segments_json")
    op.drop_column("session_reports", "focus_percentage")
