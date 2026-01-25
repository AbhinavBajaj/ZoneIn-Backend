"""Session report model (aggregated, privacy-first)."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionReport(Base):
    __tablename__ = "session_reports"
    __table_args__ = (UniqueConstraint("user_id", "session_id", name="uq_session_reports_user_session"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # UUID from macOS app
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    focused_sec: Mapped[float] = mapped_column(Float, nullable=False)
    distracted_sec: Mapped[float] = mapped_column(Float, nullable=False)
    neutral_sec: Mapped[float] = mapped_column(Float, nullable=False)
    zone_in_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0–100
    timeline_buckets_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of buckets
    cloud_ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="reports")
