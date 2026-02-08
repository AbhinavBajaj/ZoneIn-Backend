"""Backfill user.total_focused_sec from sum of session_reports.focused_sec per user.
Run after adding total_focused_sec to users:
  python backfill_total_focused_sec.py
"""
from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.models.user import User
from app.models.session_report import SessionReport


def main() -> None:
    db = SessionLocal()
    try:
        # Sum focused_sec per user
        subq = (
            select(SessionReport.user_id, func.sum(SessionReport.focused_sec).label("total"))
            .group_by(SessionReport.user_id)
        ).subquery()
        rows = db.execute(select(User.id, subq.c.total).join(subq, User.id == subq.c.user_id)).all()
        for user_id, total in rows:
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if user:
                user.total_focused_sec = float(total or 0)
                print(f"User {user_id}: total_focused_sec = {user.total_focused_sec}")
        db.commit()
        print(f"Updated total_focused_sec for {len(rows)} user(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
