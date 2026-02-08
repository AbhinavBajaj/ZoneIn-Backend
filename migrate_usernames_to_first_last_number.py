"""Migrate existing usernames to firstname_lastname_N format.

Run once on local and prod DBs. Processes users in created_at order so N is
chronological (first user with that first+last gets _1, etc.).

Usage:
  python migrate_usernames_to_first_last_number.py [--dry-run]
"""
import argparse
import sys
from collections import defaultdict
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User
from app.services.username import name_to_base


def migrate_usernames(dry_run: bool = False):
    db = SessionLocal()
    try:
        users = db.execute(
            select(User).order_by(User.created_at.asc())
        ).scalars().all()

        # Per base (firstname_lastname), assign N in created_at order
        next_n: dict[str, int] = defaultdict(lambda: 1)
        updates: list[tuple[User, str]] = []

        for user in users:
            name_to_use = user.name or (user.email.split("@")[0] if user.email else "user")
            base = name_to_base(name_to_use)
            n = next_n[base]
            next_n[base] += 1
            new_username = f"{base}_{n}"
            if user.username != new_username:
                updates.append((user, new_username))

        if not updates:
            print("No usernames to update.")
            return

        print(f"Will update {len(updates)} user(s) to new format (firstname_lastname_N):")
        for user, new_username in updates:
            print(f"  {user.email or user.google_sub}: {user.username or '(null)'} -> {new_username}")

        if dry_run:
            print("\n[DRY RUN] No changes written. Run without --dry-run to apply.")
            return

        for user, new_username in updates:
            user.username = new_username
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
