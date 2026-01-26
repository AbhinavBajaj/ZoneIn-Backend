"""JWT encode/decode and auth dependency."""
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
Bearer = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    sub: str  # user id (uuid)
    exp: datetime | None = None


def create_access_token(user_id: UUID) -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return TokenPayload(sub=payload["sub"], exp=datetime.fromtimestamp(payload["exp"]))
    except (JWTError, KeyError):
        return None


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(Bearer)],
) -> UUID:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        return UUID(payload.sub)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_optional_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(Bearer)],
) -> UUID | None:
    """Get current user ID if authenticated, otherwise return None."""
    if not credentials or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    try:
        return UUID(payload.sub)
    except ValueError:
        return None
