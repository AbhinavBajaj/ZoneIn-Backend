"""Authenticated /me."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models.user import User

router = APIRouter(tags=["me"])


@router.get("/me")
def me(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        return {"id": str(user_id), "email": None, "name": None}
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
    }
