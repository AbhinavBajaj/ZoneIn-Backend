"""Backfill usernames for existing users who don't have one."""
import sys
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User
from app.services.username import generate_unique_username


def backfill_usernames():
    """Backfill usernames for all users who don't have one."""
    db = SessionLocal()
    try:
        # Find all users without usernames
        users_without_username = db.execute(
            select(User).where(User.username.is_(None))
        ).scalars().all()
        
        print(f"Found {len(users_without_username)} users without usernames")
        
        for user in users_without_username:
            # Generate username based on name or email
            name_to_use = user.name or (user.email.split("@")[0] if user.email else "user")
            username = generate_unique_username(db, name_to_use)
            user.username = username
            print(f"  Generated username '{username}' for user {user.email or user.google_sub}")
        
        db.commit()
        print(f"\nSuccessfully backfilled {len(users_without_username)} usernames")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_usernames()
