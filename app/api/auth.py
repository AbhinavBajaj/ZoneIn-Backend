"""Google OAuth login + callback, JWT issuance."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.database import get_db
from app.models.user import User
from app.services.google_oauth import build_authorization_url, fetch_token_and_user, generate_state
from app.services.oauth_state import check_state, set_state

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login")
def google_login(request: Request, redirect_ui: str | None = None):
    state = generate_state()
    set_state(state, redirect_ui)
    url = build_authorization_url(state)
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    ok, redirect_ui_stored = check_state(state)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    try:
        sub, email, name = await fetch_token_and_user(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {e}") from e

    row = db.execute(select(User).where(User.google_sub == sub)).scalar_one_or_none()
    if row:
        user = row
        if email is not None:
            user.email = email
        if name is not None:
            user.name = name
        db.commit()
        db.refresh(user)
    else:
        user = User(google_sub=sub, email=email or "", name=name or "")
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id)
    ui_base = redirect_ui_stored or request.query_params.get("redirect_ui", "http://localhost:5000")
    return RedirectResponse(url=f"{ui_base.rstrip('/')}/signin?token={token}")


