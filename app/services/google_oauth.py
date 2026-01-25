"""Google OAuth (OpenID Connect) flow."""
import secrets

import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings

SCOPES = "openid email profile"


def build_authorization_url(state: str) -> str:
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    params = [
        ("client_id", settings.google_client_id),
        ("redirect_uri", f"{settings.base_url.rstrip('/')}/auth/google/callback"),
        ("response_type", "code"),
        ("scope", SCOPES),
        ("state", state),
        ("access_type", "offline"),
        ("prompt", "consent"),
    ]
    q = "&".join(f"{k}={v}" for k, v in params)
    return f"{base}?{q}"


def generate_state() -> str:
    return secrets.token_urlsafe(32)


async def fetch_token_and_user(code: str) -> tuple[str, str | None, str | None]:
    """Exchange code for tokens, verify id_token, return (sub, email, name)."""
    redirect_uri = f"{settings.base_url.rstrip('/')}/auth/google/callback"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    r.raise_for_status()
    data = r.json()
    id_token_jwt = data.get("id_token")
    if not id_token_jwt:
        raise ValueError("No id_token in response")

    idinfo = id_token.verify_oauth2_token(
        id_token_jwt,
        google_requests.Request(),
        settings.google_client_id,
    )
    sub = idinfo.get("sub")
    if not sub:
        raise ValueError("No sub in id_token")
    return sub, idinfo.get("email"), idinfo.get("name")
