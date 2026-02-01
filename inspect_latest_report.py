#!/usr/bin/env python3
"""
Inspect the latest session report from the DB: timeline events (including Chrome URLs)
and half_focused_segments_json. Use this to verify the backend has all data for the report.

Run from ZoneIn-Backend (so the backend's DB is used):
  cd ZoneIn-Backend
  python inspect_latest_report.py

Raw SQLite must use the backend's DB file (ZoneIn-Backend/zonein.db), not the macOS app's.
"""
import json
import os
import sys

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.session_report import SessionReport


def main() -> None:
    # Show which DB we're using (helps when you have multiple zonein.db files)
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        path = db_url.replace("sqlite:///", "").strip("/")
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        print(f"DB: {path}")
        if not os.path.exists(path):
            print("  (file does not exist yet; run the backend once or: alembic upgrade head)")
            return
    else:
        print(f"DB: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print()

    db = SessionLocal()
    try:
        report = db.query(SessionReport).order_by(SessionReport.ended_at.desc()).first()
        if not report:
            print("No reports in DB.")
            return
        print(f"Latest report: id={report.id} session_id={report.session_id} ended_at={report.ended_at}")
        print()

        # Timeline (includes Chrome/browser events with url)
        raw = report.timeline_buckets_json
        if raw:
            try:
                events = json.loads(raw)
                if isinstance(events, list):
                    print("Timeline events (Chrome URLs are in kind='browser' events):")
                    for i, ev in enumerate(events):
                        kind = ev.get("kind", "?")
                        label = ev.get("label", "?")
                        url = ev.get("url")
                        state = ev.get("state", "?")
                        start = ev.get("start_ts")
                        end = ev.get("end_ts")
                        dur = (end - start) if isinstance(start, (int, float)) and isinstance(end, (int, float)) else None
                        line = f"  [{i}] kind={kind} label={label!r} state={state}"
                        if dur is not None:
                            line += f" duration={dur:.0f}s"
                        if url:
                            line += f" url={url}"
                        print(line)
                else:
                    print("timeline_buckets_json is not a list:", type(events))
            except json.JSONDecodeError as e:
                print("timeline_buckets_json invalid JSON:", e)
        else:
            print("timeline_buckets_json is empty")

        print()

        # Half/full focus segments
        segs_raw = getattr(report, "half_focused_segments_json", None)
        if segs_raw:
            try:
                segs = json.loads(segs_raw)
                if isinstance(segs, list):
                    print("Focus segments (half_focused_segments_json):")
                    for s in segs:
                        print(f"  {s.get('state', '?')} apps_display={s.get('apps_display', '?')!r} start_ts={s.get('start_ts')} end_ts={s.get('end_ts')}")
                else:
                    print("half_focused_segments_json is not a list")
            except json.JSONDecodeError as e:
                print("half_focused_segments_json invalid JSON:", e)
        else:
            print("half_focused_segments_json is empty")
    finally:
        db.close()


if __name__ == "__main__":
    main()
