"""User model (Google OAuth)."""
import uuid
from datetime import date, datetime
from sqlalchemy import String, DateTime, Date, UUID, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)  # Profile picture URL
    max_zone_in_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    total_focused_sec: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)  # Sum of focused_sec across all reports
    streak_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Consecutive days with activity
    last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # UTC date of last activity (report)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    reports: Mapped[list["SessionReport"]] = relationship("SessionReport", back_populates="user")
    reactions: Mapped[list["Reaction"]] = relationship("Reaction", back_populates="user")
