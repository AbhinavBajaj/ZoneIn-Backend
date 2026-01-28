"""User model (Google OAuth)."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, UUID, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    max_zone_in_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    reports: Mapped[list["SessionReport"]] = relationship("SessionReport", back_populates="user")
    reactions: Mapped[list["Reaction"]] = relationship("Reaction", back_populates="user")
