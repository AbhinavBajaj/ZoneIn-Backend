"""add max_zone_in_score to users

Revision ID: add_max_zone_in_score_to_users
Revises: add_username_to_users
Create Date: 2026-01-27 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_max_zone_in_score_to_users"
down_revision: Union[str, Sequence[str], None] = "add_username_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("max_zone_in_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "max_zone_in_score")
