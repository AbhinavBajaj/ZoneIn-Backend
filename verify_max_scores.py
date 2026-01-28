"""Verify max_zone_in_score values for all users."""
from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.user import User
from app.models.session_report import SessionReport

def verify_max_scores():
    """Check max_zone_in_score values for all users."""
    db = SessionLocal()
    try:
        # Get all users
        users = db.execute(select(User)).scalars().all()
        
        print(f"Total users: {len(users)}\n")
        
        for user in users:
            # Get max zone_in_score from all their reports
            max_score_query = (
                select(func.max(SessionReport.zone_in_score))
                .where(SessionReport.user_id == user.id)
            )
            actual_max = db.execute(max_score_query).scalar_one_or_none()
            
            stored_max = user.max_zone_in_score
            
            status = "✓" if stored_max == actual_max else "✗"
            print(f"{status} User {user.id}")
            print(f"   Email/Username: {user.email or user.username or 'unknown'}")
            print(f"   Stored max_zone_in_score: {stored_max}")
            print(f"   Actual max from reports: {actual_max}")
            if stored_max != actual_max:
                print(f"   ⚠️  MISMATCH!")
            print()
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_max_scores()
