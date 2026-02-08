"""add avatar_url to users

Revision ID: add_avatar_url
Revises: add_published_at
Create Date: 2026-02-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_avatar_url"
down_revision: Union[str, Sequence[str], None] = "add_published_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
