"""Seed production database with initial data."""
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User
from app.models.session_report import SessionReport
from app.services.username import generate_unique_username

def seed_production():
    """Seed the database with initial user and report."""
    db = SessionLocal()
    try:
        # Check if user already exists
        user = db.execute(
            select(User).where(User.email == "abhinav.bajaj2023@gmail.com")
        ).scalar_one_or_none()
        
        if not user:
            print("Creating user: abhinav.bajaj2023@gmail.com")
            # Use the actual google_sub from local database
            # This is the google_sub for abhinav.bajaj2023@gmail.com
            google_sub = "107324490320939771989"
            
            user = User(
                google_sub=google_sub,
                email="abhinav.bajaj2023@gmail.com",
                name="Abhinav Bajaj",
            )
            # Generate username
            user.username = generate_unique_username(db, user.name)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ User created with username: {user.username}")
        else:
            # Ensure user has username
            if not user.username:
                user.username = generate_unique_username(db, user.name or "user")
                db.commit()
                db.refresh(user)
                print(f"✅ Username generated: {user.username}")
            else:
                print(f"✅ User already exists with username: {user.username}")
        
        # Check if report already exists
        existing_report = db.execute(
            select(SessionReport).where(
                SessionReport.user_id == user.id,
                SessionReport.zone_in_score == 95.0
            ).limit(1)
        ).scalar_one_or_none()
        
        if not existing_report:
            print("Creating sample report with 95% ZoneIn score...")
            # Create a sample report with 95% focus
            # For 95% score, we need: focus% = 95% (or slightly less with bonus)
            # Let's say 4 hours session with 95% focus = 95% score
            duration_sec = 4 * 3600  # 4 hours
            focused_sec = duration_sec * 0.95  # 95% focused
            distracted_sec = duration_sec * 0.03  # 3% distracted
            neutral_sec = duration_sec * 0.02  # 2% neutral
            snoozed_sec = 0.0
            
            # Calculate zone_in_score to be exactly 95%
            # ZoneIn score = (focused / active_duration) * 100 + bonus
            # For exactly 95%, we can use: base_score = 95% (no bonus needed)
            active_duration = duration_sec - snoozed_sec
            base_score = (focused_sec / active_duration) * 100 if active_duration > 0 else 0
            # Ensure we get exactly 95%
            zone_in_score = 95.0
            
            # Create timeline buckets (simplified)
            timeline_buckets = [
                {
                    "bucket_start_ts": 0,
                    "bucket_duration_sec": int(focused_sec),
                    "state": "focused"
                },
                {
                    "bucket_start_ts": int(focused_sec),
                    "bucket_duration_sec": int(distracted_sec),
                    "state": "distracted"
                },
                {
                    "bucket_start_ts": int(focused_sec + distracted_sec),
                    "bucket_duration_sec": int(neutral_sec),
                    "state": "neutral"
                }
            ]
            
            import json
            started_at = datetime.now(timezone.utc) - timedelta(hours=4)
            ended_at = datetime.now(timezone.utc)
            
            report = SessionReport(
                user_id=user.id,
                session_id="production-seed-001",
                started_at=started_at,
                ended_at=ended_at,
                duration_sec=duration_sec,
                focused_sec=focused_sec,
                distracted_sec=distracted_sec,
                neutral_sec=neutral_sec,
                snoozed_sec=snoozed_sec,
                zone_in_score=zone_in_score,
                timeline_buckets_json=json.dumps(timeline_buckets),
                cloud_ai_enabled=False,
                published=False,
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            print(f"✅ Sample report created with {zone_in_score}% ZoneIn score")
            print(f"   Report ID: {report.id}")
        else:
            print("✅ Sample report already exists")
        
        print("\n✅ Production database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_production()
