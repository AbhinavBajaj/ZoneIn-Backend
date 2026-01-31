#!/usr/bin/env python3
"""Delete all reports and all reactions (public report reactions) from the database."""
import sys
from sqlalchemy import delete
from app.core.database import SessionLocal
from app.models.reaction import Reaction
from app.models.session_report import SessionReport


def main():
    db = SessionLocal()
    try:
        # Delete all reactions first (reactions on published reports)
        reactions_result = db.execute(delete(Reaction))
        n_reactions = reactions_result.rowcount

        # Delete all reports (private and published)
        reports_result = db.execute(delete(SessionReport))
        n_reports = reports_result.rowcount

        db.commit()
        print(f"✅ Deleted {n_reactions} reaction(s) and {n_reports} report(s) from the database.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
