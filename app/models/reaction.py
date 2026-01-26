"""Reaction model for leaderboard emoji reactions."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UUID, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("user_id", "report_id", name="uq_reactions_user_report"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("session_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    emoji: Mapped[str] = mapped_column(String(10), nullable=False)  # Store emoji as string (e.g., "👏", "🔥")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="reactions")
    report: Mapped["SessionReport"] = relationship("SessionReport", back_populates="reactions")
