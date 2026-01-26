"""add published field and reactions table

Revision ID: add_published_and_reactions
Revises: add_snoozed_sec
Create Date: 2026-01-25 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_published_and_reactions"
down_revision: Union[str, Sequence[str], None] = "add_snoozed_sec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add published field to session_reports
    op.add_column("session_reports", sa.Column("published", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index(op.f("ix_session_reports_published"), "session_reports", ["published"], unique=False)
    
    # Create reactions table
    op.create_table(
        "reactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("emoji", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["session_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "report_id", name="uq_reactions_user_report"),
    )
    op.create_index(op.f("ix_reactions_user_id"), "reactions", ["user_id"], unique=False)
    op.create_index(op.f("ix_reactions_report_id"), "reactions", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reactions_report_id"), table_name="reactions")
    op.drop_index(op.f("ix_reactions_user_id"), table_name="reactions")
    op.drop_table("reactions")
    op.drop_index(op.f("ix_session_reports_published"), table_name="session_reports")
    op.drop_column("session_reports", "published")
