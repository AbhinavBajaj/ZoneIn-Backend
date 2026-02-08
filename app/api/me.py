"""Authenticated /me."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.avatar import default_avatar_url_for_user
from app.core.database import get_db
from app.models.user import User
from app.models.session_report import SessionReport
from app.api.reports import _top_focus_app_from_segments

router = APIRouter(tags=["me"])


class UpdateMeBody(BaseModel):
    avatar_url: str | None = None  # Profile picture URL; set to null to clear


def _latest_report_info(db: Session, user_id: UUID):
    """Return (top_focus_app, last_activity_at) from user's most recent report."""
    latest = (
        db.execute(
            select(SessionReport)
            .where(SessionReport.user_id == user_id)
            .order_by(SessionReport.ended_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    if not latest:
        return None, None
    top = _top_focus_app_from_segments(latest.half_focused_segments_json)
    last_at = latest.published_at if latest.published_at else latest.ended_at
    return top, last_at


@router.get("/me")
def me(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        return {"id": str(user_id), "email": None, "name": None, "username": None, "avatar_url": None, "total_focused_sec": None, "top_focus_app": None, "last_activity_at": None}
    top_focus_app, last_activity_at = _latest_report_info(db, user_id)
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "username": user.username,
        "avatar_url": getattr(user, "avatar_url", None),
        "total_focused_sec": getattr(user, "total_focused_sec", None),
        "top_focus_app": top_focus_app,
        "last_activity_at": last_activity_at.isoformat() if last_activity_at else None,
    }


@router.patch("/me")
def update_me(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    body: UpdateMeBody,
):
    """Update current user profile (e.g. avatar_url)."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        return {"id": str(user_id), "email": None, "name": None, "username": None, "avatar_url": default_avatar_url_for_user(user_id)}
    if body.avatar_url is not None:
        # Allow empty string to clear
        user.avatar_url = body.avatar_url.strip() or None if isinstance(body.avatar_url, str) else None
    db.commit()
    db.refresh(user)
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "username": user.username,
        "avatar_url": getattr(user, "avatar_url", None) or default_avatar_url_for_user(user.id),
    }
