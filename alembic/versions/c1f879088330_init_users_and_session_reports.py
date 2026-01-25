"""init users and session_reports

Revision ID: c1f879088330
Revises:
Create Date: 2026-01-24 20:09:08.832292

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1f879088330"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("google_sub", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_google_sub"), "users", ["google_sub"], unique=True)

    op.create_table(
        "session_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_sec", sa.Float(), nullable=False),
        sa.Column("focused_sec", sa.Float(), nullable=False),
        sa.Column("distracted_sec", sa.Float(), nullable=False),
        sa.Column("neutral_sec", sa.Float(), nullable=False),
        sa.Column("zone_in_score", sa.Float(), nullable=False),
        sa.Column("timeline_buckets_json", sa.Text(), nullable=True),
        sa.Column("cloud_ai_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "session_id", name="uq_session_reports_user_session"),
    )
    op.create_index(op.f("ix_session_reports_user_id"), "session_reports", ["user_id"], unique=False)
    op.create_index(op.f("ix_session_reports_session_id"), "session_reports", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_session_reports_session_id"), table_name="session_reports")
    op.drop_index(op.f("ix_session_reports_user_id"), table_name="session_reports")
    op.drop_table("session_reports")
    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.drop_table("users")
