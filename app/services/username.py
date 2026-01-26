"""Username generation utilities."""
import secrets
import string
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def extract_first_name(name: str | None) -> str:
    """Extract first name from full name."""
    if not name:
        return "user"
    return name.split()[0].lower() if name.split() else "user"


def generate_random_suffix(length: int = 8) -> str:
    """Generate random alphanumeric string with special characters."""
    # Use alphanumeric + some safe special characters
    chars = string.ascii_lowercase + string.digits + "-_"
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_unique_username(db: Session, first_name: str) -> str:
    """Generate a unique username in format: firstname-random8chars."""
    base_name = extract_first_name(first_name)
    max_attempts = 100
    
    for _ in range(max_attempts):
        suffix = generate_random_suffix(8)
        username = f"{base_name}-{suffix}"
        
        # Check if username already exists
        existing = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        
        if not existing:
            return username
    
    # Fallback: add timestamp if we can't find unique username
    import time
    timestamp = str(int(time.time()))[-6:]
    return f"{base_name}-{timestamp}"
