"""Backfill max_zone_in_score for all users based on their reports."""
import sys
from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.user import User
from app.models.session_report import SessionReport

def backfill_max_scores():
    """Calculate and set max_zone_in_score for all users."""
    db = SessionLocal()
    try:
        # Get all users
        users = db.execute(select(User)).scalars().all()
        
        for user in users:
            # Get max zone_in_score from all their reports
            max_score_query = (
                select(func.max(SessionReport.zone_in_score))
                .where(SessionReport.user_id == user.id)
            )
            max_score = db.execute(max_score_query).scalar_one_or_none()
            
            if max_score is not None:
                user.max_zone_in_score = max_score
                print(f"Updated user {user.id} ({user.email or user.username or 'unknown'}): max_zone_in_score = {max_score}")
            else:
                print(f"User {user.id} ({user.email or user.username or 'unknown'}): no reports found")
        
        db.commit()
        print(f"\nBackfill completed for {len(users)} users")
    except Exception as e:
        db.rollback()
        print(f"Error during backfill: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    backfill_max_scores()
