"""add snoozed_sec to session_reports

Revision ID: add_snoozed_sec
Revises: c1f879088330
Create Date: 2026-01-25 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_snoozed_sec"
down_revision: Union[str, Sequence[str], None] = "c1f879088330"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_reports", sa.Column("snoozed_sec", sa.Float(), nullable=False, server_default="0.0"))


def downgrade() -> None:
    op.drop_column("session_reports", "snoozed_sec")
