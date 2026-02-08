"""Authenticated /me."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models.user import User

router = APIRouter(tags=["me"])


class UpdateMeBody(BaseModel):
    avatar_url: str | None = None  # Profile picture URL; set to null to clear


@router.get("/me")
def me(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        return {"id": str(user_id), "email": None, "name": None, "username": None, "avatar_url": None}
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "username": user.username,
        "avatar_url": getattr(user, "avatar_url", None),
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
        return {"id": str(user_id), "email": None, "name": None, "username": None, "avatar_url": None}
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
        "avatar_url": getattr(user, "avatar_url", None),
    }
