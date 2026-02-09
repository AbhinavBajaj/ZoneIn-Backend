"""Backfill user.streak_count and user.last_activity_date for existing users.
Users who have at least one report get streak_count=1 and last_activity_date = date of latest report (UTC).
Run after adding streak_count and last_activity_date to users:
  python backfill_streak.py
"""
from datetime import timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import User
from app.models.session_report import SessionReport


def main() -> None:
    db = SessionLocal()
    try:
        users = db.execute(select(User)).scalars().all()
        updated = 0
        for user in users:
            latest = (
                db.execute(
                    select(SessionReport)
                    .where(SessionReport.user_id == user.id)
                    .order_by(SessionReport.ended_at.desc())
                    .limit(1)
                )
                .scalar_one_or_none()
            )
            if latest:
                ended = latest.ended_at
                activity_date = ended.date() if ended.tzinfo else ended.replace(tzinfo=timezone.utc).date()
                user.streak_count = 1
                user.last_activity_date = activity_date
                updated += 1
                print(f"User {user.username or user.id}: streak_count=1, last_activity_date={activity_date}")
        db.commit()
        print(f"Backfilled streak for {updated} user(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
