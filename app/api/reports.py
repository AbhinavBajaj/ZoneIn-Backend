"""Session reports API (create, list, get, delete)."""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id, get_optional_user_id
from app.core.database import get_db
from app.models.session_report import SessionReport
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


class TimelineBucket(BaseModel):
    bucket_start_ts: float = Field(..., description="Unix timestamp (seconds)")
    bucket_duration_sec: int = Field(..., ge=1, le=3600)
    state: str = Field(..., pattern="^(focused|distracted|neutral|snoozed)$")


class ReportCreate(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    started_at: datetime
    ended_at: datetime
    duration_sec: float = Field(..., ge=0)
    focused_sec: float = Field(..., ge=0)
    distracted_sec: float = Field(..., ge=0)
    neutral_sec: float = Field(..., ge=0)
    snoozed_sec: float = Field(0, ge=0)  # Optional, defaults to 0 for backward compatibility
    zone_in_score: float = Field(..., ge=0, le=100)
    focus_percentage: float | None = Field(None, ge=0, le=100)  # From app; FE uses this instead of recomputing
    timeline_buckets_json: str | None = None  # JSON array of TimelineBucket
    half_focused_segments_json: str | None = None  # JSON array of { start_ts, end_ts, apps_display }
    cloud_ai_enabled: bool = False


class ReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    started_at: datetime
    ended_at: datetime
    duration_sec: float
    focused_sec: float
    distracted_sec: float
    neutral_sec: float
    snoozed_sec: float
    zone_in_score: float
    focus_percentage: float | None = None
    timeline_buckets_json: str | None
    half_focused_segments_json: str | None = None
    cloud_ai_enabled: bool
    published: bool
    activity_public: bool = False
    created_at: datetime
    is_own_report: bool = True
    # When activity is redacted (non-owner, activity_public=False), only these are set:
    timeline_public_json: str | None = None  # state-only timeline for bar
    top_focus_app: str | None = None


# Bundle ID / label for Chrome app (macOS); if this app event is followed by a browser event,
# we assume the Chrome event was a missed tab and override it with the next browser event.
CHROME_APP_BUNDLE_ID = "com.google.Chrome"
CHROME_APP_LABEL = "Google Chrome"


def _is_chrome_app_event(ev: dict) -> bool:
    kind = ev.get("kind") or ""
    bundle = ev.get("bundle_id") or ""
    label = ev.get("label") or ""
    return (
        kind == "app"
        and (bundle == CHROME_APP_BUNDLE_ID or label == CHROME_APP_LABEL)
    )


def _is_browser_event_with_url(ev: dict) -> bool:
    kind = ev.get("kind") or ""
    return kind == "browser" and (ev.get("url") is not None or ev.get("label") is not None)


def _override_chrome_with_browser(chrome_ev: dict, browser_ev: dict) -> None:
    """Overwrite Chrome app event with browser event's url, label, classification."""
    chrome_ev["kind"] = "browser"
    chrome_ev["classification"] = browser_ev.get("classification") if browser_ev.get("classification") is not None else "neutral"
    chrome_ev["label"] = browser_ev.get("label") if browser_ev.get("label") is not None else chrome_ev.get("label", "")
    chrome_ev["url"] = browser_ev.get("url")
    if "bundle_id" in chrome_ev:
        del chrome_ev["bundle_id"]


def _normalize_timeline_chrome_override(timeline_buckets_json: str | None) -> str | None:
    """
    If a Google Chrome app event is immediately before or after a browser event (with url),
    override the Chrome event with that browser event's classification, url, and label
    (user was on that page; the extension event was delayed or missed when switching).
    """
    if not timeline_buckets_json or not timeline_buckets_json.strip():
        return timeline_buckets_json
    try:
        events = json.loads(timeline_buckets_json)
    except (json.JSONDecodeError, TypeError):
        return timeline_buckets_json
    if not isinstance(events, list) or len(events) < 2:
        return timeline_buckets_json
    modified = False
    for i in range(len(events) - 1):
        prev = events[i]
        curr = events[i + 1]
        if not isinstance(prev, dict) or not isinstance(curr, dict):
            continue
        # Case 1: prev = Chrome app, curr = browser with url -> override prev with curr
        if _is_chrome_app_event(prev) and _is_browser_event_with_url(curr):
            _override_chrome_with_browser(prev, curr)
            modified = True
            logger.debug(
                "Overrode Chrome app (prev) with next browser event: label=%s url=%s",
                prev.get("label"),
                prev.get("url"),
            )
        # Case 2: prev = browser with url, curr = Chrome app -> override curr with prev
        elif _is_browser_event_with_url(prev) and _is_chrome_app_event(curr):
            _override_chrome_with_browser(curr, prev)
            modified = True
            logger.debug(
                "Overrode Chrome app (curr) with prev browser event: label=%s url=%s",
                curr.get("label"),
                curr.get("url"),
            )
    if not modified:
        return timeline_buckets_json
    return json.dumps(events)


def _update_user_max_score(db: Session, user_id: UUID, new_score: float) -> None:
    """Update user's max_zone_in_score if the new score is higher."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user:
        old_score = user.max_zone_in_score
        if user.max_zone_in_score is None or new_score > user.max_zone_in_score:
            user.max_zone_in_score = new_score
            db.commit()
            logger.info("Updated max_zone_in_score for user_id=%s: %s -> %s", user_id, old_score, new_score)


def _update_user_total_focused(db: Session, user_id: UUID) -> None:
    """Set user's total_focused_sec to the sum of focused_sec across all their reports."""
    total = db.execute(
        select(func.coalesce(func.sum(SessionReport.focused_sec), 0)).where(SessionReport.user_id == user_id)
    ).scalar_one()
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user:
        user.total_focused_sec = float(total)
        db.commit()
        logger.info("Updated total_focused_sec for user_id=%s: %s", user_id, total)


def _to_out(r: SessionReport, tz_str: str | None = None) -> dict:
    """Convert report to output dict, optionally converting datetimes to local timezone."""
    started_at = r.started_at
    ended_at = r.ended_at
    created_at = r.created_at
    
    # Convert to local timezone if specified
    if tz_str:
        try:
            tz = ZoneInfo(tz_str)
            # Ensure datetimes are timezone-aware (should be UTC from DB)
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if ended_at.tzinfo is None:
                ended_at = ended_at.replace(tzinfo=timezone.utc)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            # Convert to local timezone
            started_at = started_at.astimezone(tz)
            ended_at = ended_at.astimezone(tz)
            created_at = created_at.astimezone(tz)
        except Exception as e:
            logger.warning("Invalid timezone %s: %s, using UTC", tz_str, e)
    
    return {
        "id": str(r.id),
        "session_id": r.session_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": r.duration_sec,
        "focused_sec": r.focused_sec,
        "distracted_sec": r.distracted_sec,
        "neutral_sec": r.neutral_sec,
        "snoozed_sec": getattr(r, "snoozed_sec", 0.0),  # Backward compatibility
        "zone_in_score": r.zone_in_score,
        "focus_percentage": getattr(r, "focus_percentage", None),
        "timeline_buckets_json": r.timeline_buckets_json,
        "half_focused_segments_json": getattr(r, "half_focused_segments_json", None),
        "cloud_ai_enabled": r.cloud_ai_enabled,
        "published": getattr(r, "published", False),  # Backward compatibility
        "published_at": getattr(r, "published_at", None),  # When report was published
        "activity_public": getattr(r, "activity_public", False),
        "created_at": created_at,
    }


def _state_only_timeline(timeline_buckets_json: str | None) -> str | None:
    """Strip timeline to only start_ts, end_ts, state for public bar (no app/label/url)."""
    if not timeline_buckets_json or not timeline_buckets_json.strip():
        return None
    try:
        events = json.loads(timeline_buckets_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(events, list):
        return None
    out = []
    for o in events:
        if not isinstance(o, dict) or "start_ts" not in o or "end_ts" not in o:
            continue
        out.append({
            "start_ts": o["start_ts"],
            "end_ts": o["end_ts"],
            "state": o.get("state", "neutral"),
        })
    return json.dumps(out) if out else None


def _top_focus_app_from_segments(half_focused_segments_json: str | None) -> str | None:
    """Compute top focus app (most focused time) from half_focused_segments with state focused."""
    if not half_focused_segments_json or not half_focused_segments_json.strip():
        return None
    try:
        arr = json.loads(half_focused_segments_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(arr, list):
        return None
    total_by_app: dict[str, float] = {}
    for o in arr:
        if not isinstance(o, dict):
            continue
        state = o.get("state", "half_focused")
        if state != "focused":
            continue
        start_ts = o.get("start_ts")
        end_ts = o.get("end_ts")
        apps_display = o.get("apps_display") or ""
        if not isinstance(start_ts, (int, float)) or not isinstance(end_ts, (int, float)):
            continue
        dur = float(end_ts - start_ts)
        total_by_app[apps_display] = total_by_app.get(apps_display, 0) + dur
    if not total_by_app:
        return None
    return max(total_by_app, key=total_by_app.get)


@router.post("", response_model=ReportOut)
def create_report(
    body: ReportCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    tz: str | None = Query(None, alias="timezone", description="IANA timezone e.g. America/New_York; convert response datetimes to this timezone"),
):
    # Ensure datetimes are timezone-aware and convert to UTC for storage
    started_at = body.started_at
    ended_at = body.ended_at
    
    # If timezone-naive, assume UTC (macOS app should send timezone-aware)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC if it has timezone info
        started_at = started_at.astimezone(timezone.utc)
    
    if ended_at.tzinfo is None:
        ended_at = ended_at.replace(tzinfo=timezone.utc)
    else:
        ended_at = ended_at.astimezone(timezone.utc)
    
    existing = db.execute(
        select(SessionReport).where(
            SessionReport.user_id == user_id,
            SessionReport.session_id == body.session_id,
        )
    ).scalar_one_or_none()

    timeline_json = _normalize_timeline_chrome_override(body.timeline_buckets_json) or body.timeline_buckets_json

    if existing:
        existing.started_at = started_at
        existing.ended_at = ended_at
        existing.duration_sec = body.duration_sec
        existing.focused_sec = body.focused_sec
        existing.distracted_sec = body.distracted_sec
        existing.neutral_sec = body.neutral_sec
        existing.snoozed_sec = body.snoozed_sec
        existing.zone_in_score = body.zone_in_score
        existing.focus_percentage = body.focus_percentage
        existing.timeline_buckets_json = timeline_json
        existing.half_focused_segments_json = body.half_focused_segments_json
        existing.cloud_ai_enabled = body.cloud_ai_enabled
        db.commit()
        db.refresh(existing)
        _update_user_max_score(db, user_id, body.zone_in_score)
        _update_user_total_focused(db, user_id)
        out = _to_out(existing, tz)
        logger.info("Report updated: session_id=%s user_id=%s", body.session_id, user_id)
        logger.info("POST /reports upsert struct: %s", json.dumps(out, default=str))
        return out

    r = SessionReport(
        user_id=user_id,
        session_id=body.session_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_sec=body.duration_sec,
        focused_sec=body.focused_sec,
        distracted_sec=body.distracted_sec,
        neutral_sec=body.neutral_sec,
        snoozed_sec=body.snoozed_sec,
        zone_in_score=body.zone_in_score,
        focus_percentage=body.focus_percentage,
        timeline_buckets_json=timeline_json,
        half_focused_segments_json=body.half_focused_segments_json,
        cloud_ai_enabled=body.cloud_ai_enabled,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    _update_user_max_score(db, user_id, body.zone_in_score)
    _update_user_total_focused(db, user_id)
    out = _to_out(r, tz)
    logger.info("Report created: session_id=%s user_id=%s id=%s", body.session_id, user_id, r.id)
    logger.info("POST /reports create struct: %s", json.dumps(out, default=str))
    return out


def _parse_date_range(
    from_date: date | None,
    to_date: date | None,
    tz_str: str | None,
) -> tuple[datetime | None, datetime | None]:
    """Build UTC datetimes for filtering. If tz_str given, interpret from/to as local dates."""
    tz = ZoneInfo(tz_str) if tz_str else timezone.utc
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    if from_date is not None:
        from_dt = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0, 0, tzinfo=tz)
        from_dt = from_dt.astimezone(timezone.utc)
    if to_date is not None:
        end_next = to_date + timedelta(days=1)
        to_dt = datetime(end_next.year, end_next.month, end_next.day, 0, 0, 0, 0, tzinfo=tz)
        to_dt = to_dt.astimezone(timezone.utc)
    return from_dt, to_dt


@router.get("", response_model=list[ReportOut])
def list_reports(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    tz: str | None = Query(None, alias="timezone", description="IANA timezone e.g. America/New_York; from/to are local dates, response datetimes converted to this timezone"),
):
    q = select(SessionReport).where(SessionReport.user_id == user_id)
    from_dt, to_dt = _parse_date_range(from_date, to_date, tz)
    if from_dt is not None:
        q = q.where(SessionReport.ended_at >= from_dt)
    if to_dt is not None:
        q = q.where(SessionReport.started_at < to_dt)
    q = q.order_by(SessionReport.started_at.desc())
    rows = db.execute(q).scalars().all()
    out = [_to_out(r, tz) for r in rows]
    logger.info(
        "GET /reports from=%s to=%s timezone=%s -> %d reports",
        from_date,
        to_date,
        tz,
        len(out),
    )
    return out


class ActivityPublicUpdate(BaseModel):
    activity_public: bool


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: UUID,
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)],
    db: Annotated[Session, Depends(get_db)],
    tz: str | None = Query(None, alias="timezone", description="IANA timezone e.g. America/New_York; convert response datetimes to this timezone"),
):
    r = db.execute(select(SessionReport).where(SessionReport.id == report_id)).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    # Published reports: anyone can view (with or without sign-in). Unpublished: only owner.
    if not r.published:
        if user_id is None or r.user_id != user_id:
            raise HTTPException(status_code=404, detail="Report not found")
    is_own = user_id is not None and r.user_id == user_id
    activity_public = getattr(r, "activity_public", False)
    out = _to_out(r, tz)
    out["is_own_report"] = is_own
    # Redact activity for non-owners when activity is not public
    if not is_own and not activity_public:
        out["timeline_public_json"] = _state_only_timeline(r.timeline_buckets_json)
        out["top_focus_app"] = _top_focus_app_from_segments(r.half_focused_segments_json)
        out["timeline_buckets_json"] = None
        out["half_focused_segments_json"] = None
    return ReportOut(**out)


@router.patch("/{report_id}", response_model=ReportOut)
def update_report_activity_public(
    report_id: UUID,
    body: ActivityPublicUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    tz: str | None = Query(None, alias="timezone", description="IANA timezone e.g. America/New_York"),
):
    """Update activity_public (owner only)."""
    r = db.execute(
        select(SessionReport).where(
            SessionReport.id == report_id,
            SessionReport.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    r.activity_public = body.activity_public
    db.commit()
    db.refresh(r)
    out = _to_out(r, tz)
    out["is_own_report"] = True
    return ReportOut(**out)
