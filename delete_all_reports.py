#!/usr/bin/env python3
"""Delete all reports from the database."""
import sys
from sqlalchemy import delete
from app.core.database import SessionLocal, engine
from app.models.session_report import SessionReport

def main():
    db = SessionLocal()
    try:
        # Delete all reports
        result = db.execute(delete(SessionReport))
        db.commit()
        n = result.rowcount
        print(f"✅ Deleted {n} report(s) from the database.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
