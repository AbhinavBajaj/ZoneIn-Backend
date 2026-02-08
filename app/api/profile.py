"""Public profile by username (no auth required)."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.avatar import default_avatar_url_for_user
from app.core.database import get_db
from app.models.user import User
from app.models.session_report import SessionReport
from app.api.reports import _top_focus_app_from_segments

router = APIRouter(tags=["profile"])


class PublicProfileResponse(BaseModel):
    username: str | None
    avatar_url: str | None
    total_focused_sec: float | None
    max_zone_in_score: float | None
    top_focus_app: str | None = None  # From user's most recent report
    last_activity_at: datetime | None = None  # Last report ended_at (or published_at when published)


@router.get("/profile/{username}", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Get public profile by username. No auth required. Returns only public fields (no email, no subscription)."""
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    top_focus_app = None
    last_activity_at = None
    latest = (
        db.execute(
            select(SessionReport)
            .where(SessionReport.user_id == user.id)
            .order_by(SessionReport.ended_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    if latest:
        top_focus_app = _top_focus_app_from_segments(latest.half_focused_segments_json)
        last_activity_at = latest.published_at if latest.published_at else latest.ended_at

    return PublicProfileResponse(
        username=user.username,
        avatar_url=getattr(user, "avatar_url", None) or default_avatar_url_for_user(user.id),
        total_focused_sec=getattr(user, "total_focused_sec", None),
        max_zone_in_score=user.max_zone_in_score,
        top_focus_app=top_focus_app,
        last_activity_at=last_activity_at,
    )
