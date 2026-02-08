"""Public profile by username (no auth required)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.avatar import default_avatar_url_for_user
from app.core.database import get_db
from app.models.user import User

router = APIRouter(tags=["profile"])


class PublicProfileResponse(BaseModel):
    username: str | None
    avatar_url: str | None
    total_focused_sec: float | None
    max_zone_in_score: float | None


@router.get("/profile/{username}", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Get public profile by username. No auth required. Returns only public fields (no email, no subscription)."""
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return PublicProfileResponse(
        username=user.username,
        avatar_url=getattr(user, "avatar_url", None) or default_avatar_url_for_user(user.id),
        total_focused_sec=getattr(user, "total_focused_sec", None),
        max_zone_in_score=user.max_zone_in_score,
    )
