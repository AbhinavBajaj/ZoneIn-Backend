"""Migrate existing usernames to firstname_lastname_N format.

Run once on local and prod DBs. Processes users in created_at order so N is
chronological (first user with that first+last gets _1, etc.).

Usage:
  python migrate_usernames_to_first_last_number.py [--dry-run]

Loads .env from this script's directory so DATABASE_URL is taken from .env
(and not from a stale value you may have exported in your shell).
"""
import argparse
import os
import sys
from pathlib import Path
from collections import defaultdict

# Load .env from the same directory as this script *before* importing app,
# so we use the project's .env and not a stale DATABASE_URL from the shell.
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key == "DATABASE_URL" and value:
                    os.environ["DATABASE_URL"] = value
                    break

from sqlalchemy import select, update
from app.core.database import SessionLocal
from app.models.user import User
from app.services.username import name_to_base


# Only select columns that exist in all environments (prod may not have
# max_zone_in_score, total_focused_sec yet).
_USER_COLS = [User.id, User.google_sub, User.email, User.name, User.username, User.created_at]


def migrate_usernames(dry_run: bool = False):
    db = SessionLocal()
    try:
        rows = db.execute(
            select(*_USER_COLS).order_by(User.created_at.asc())
        ).all()

        # Per base (firstname_lastname), assign N in created_at order
        next_n: dict[str, int] = defaultdict(lambda: 1)
        updates: list[tuple] = []  # (user_id, email_or_sub, old_username, new_username)

        for row in rows:
            user_id, google_sub, email, name, username, _created_at = row
            name_to_use = name or (email.split("@")[0] if email else "user")
            base = name_to_base(name_to_use)
            n = next_n[base]
            next_n[base] += 1
            new_username = f"{base}_{n}"
            if username != new_username:
                updates.append((user_id, email or google_sub, username, new_username))

        if not updates:
            print("No usernames to update.")
            return

        print(f"Will update {len(updates)} user(s) to new format (firstname_lastname_N):")
        for user_id, email_or_sub, old_username, new_username in updates:
            print(f"  {email_or_sub}: {old_username or '(null)'} -> {new_username}")

        if dry_run:
            print("\n[DRY RUN] No changes written. Run without --dry-run to apply.")
            return

        for user_id, _e, _old, new_username in updates:
            db.execute(update(User).where(User.id == user_id).values(username=new_username))
        db.commit()
        print(f"\nSuccessfully updated {len(updates)} username(s).")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate usernames to firstname_lastname_N")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()
    migrate_usernames(dry_run=args.dry_run)
