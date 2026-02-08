#!/usr/bin/env python3
"""Set avatar_url for specific users in prod (by username). Run on prod with DATABASE_URL set.
Usage: python3 set_prod_avatars.py
Assigns monkey-1, monkey-2, monkey-3 to the first 3 usernames in order."""
import os
import sys

# Add project root so app imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Users to set (order = monkey-1, monkey-2, monkey-3)
USERNAMES = ["abhinav_bajaj_1", "vineeta_bajaj_1", "mary_nasimova_1"]


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: Set DATABASE_URL environment variable")
        sys.exit(1)
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        for i, username in enumerate(USERNAMES, start=1):
            avatar_url = f"/avatars/monkey-{i}.png"
            r = db.execute(
                text("UPDATE users SET avatar_url = :url WHERE username = :un"),
                {"url": avatar_url, "un": username},
            )
            db.commit()
            if r.rowcount:
                print(f"  {username} -> {avatar_url}")
            else:
                print(f"  (no user: {username})")
    finally:
        db.close()
    print("Done.")


if __name__ == "__main__":
    main()
