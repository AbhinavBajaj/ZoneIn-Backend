"""Backfill session_reports.published_at for already-published reports.
Uses report end time (ended_at) as published_at. Run after adding published_at column:
  python backfill_published_at.py
"""
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.session_report import SessionReport


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(
            select(SessionReport).where(
                SessionReport.published == True,
                SessionReport.published_at == None,
            )
        ).scalars().all()
        for report in rows:
            report.published_at = report.ended_at
            print(f"Report {report.id}: published_at = {report.ended_at}")
        db.commit()
        print(f"Backfilled published_at = ended_at for {len(rows)} published report(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
