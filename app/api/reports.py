"""Session reports API (create, list, get, delete)."""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models.session_report import SessionReport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


class TimelineBucket(BaseModel):
    bucket_start_ts: float = Field(..., description="Unix timestamp (seconds)")
    bucket_duration_sec: int = Field(..., ge=1, le=3600)
    state: str = Field(..., pattern="^(focused|distracted|neutral)$")


class ReportCreate(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    started_at: datetime
    ended_at: datetime
    duration_sec: float = Field(..., ge=0)
    focused_sec: float = Field(..., ge=0)
    distracted_sec: float = Field(..., ge=0)
    neutral_sec: float = Field(..., ge=0)
    zone_in_score: float = Field(..., ge=0, le=100)
    timeline_buckets_json: str | None = None  # JSON array of TimelineBucket
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
    zone_in_score: float
    timeline_buckets_json: str | None
    cloud_ai_enabled: bool
    created_at: datetime


def _to_out(r: SessionReport) -> dict:
    return {
        "id": str(r.id),
        "session_id": r.session_id,
        "started_at": r.started_at,
        "ended_at": r.ended_at,
        "duration_sec": r.duration_sec,
        "focused_sec": r.focused_sec,
        "distracted_sec": r.distracted_sec,
        "neutral_sec": r.neutral_sec,
        "zone_in_score": r.zone_in_score,
        "timeline_buckets_json": r.timeline_buckets_json,
        "cloud_ai_enabled": r.cloud_ai_enabled,
        "created_at": r.created_at,
    }


@router.post("", response_model=ReportOut)
def create_report(
    body: ReportCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    existing = db.execute(
        select(SessionReport).where(
            SessionReport.user_id == user_id,
            SessionReport.session_id == body.session_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.started_at = body.started_at
        existing.ended_at = body.ended_at
        existing.duration_sec = body.duration_sec
        existing.focused_sec = body.focused_sec
        existing.distracted_sec = body.distracted_sec
        existing.neutral_sec = body.neutral_sec
        existing.zone_in_score = body.zone_in_score
        existing.timeline_buckets_json = body.timeline_buckets_json
        existing.cloud_ai_enabled = body.cloud_ai_enabled
        db.commit()
        db.refresh(existing)
        out = _to_out(existing)
        logger.info("Report updated: session_id=%s user_id=%s", body.session_id, user_id)
        logger.info("POST /reports upsert struct: %s", json.dumps(out, default=str))
        return out

    r = SessionReport(
        user_id=user_id,
        session_id=body.session_id,
        started_at=body.started_at,
        ended_at=body.ended_at,
        duration_sec=body.duration_sec,
        focused_sec=body.focused_sec,
        distracted_sec=body.distracted_sec,
        neutral_sec=body.neutral_sec,
        zone_in_score=body.zone_in_score,
        timeline_buckets_json=body.timeline_buckets_json,
        cloud_ai_enabled=body.cloud_ai_enabled,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    out = _to_out(r)
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
    tz: str | None = Query(None, alias="timezone", description="IANA timezone e.g. America/Los_Angeles; from/to are local dates"),
):
    q = select(SessionReport).where(SessionReport.user_id == user_id)
    from_dt, to_dt = _parse_date_range(from_date, to_date, tz)
    if from_dt is not None:
        q = q.where(SessionReport.ended_at >= from_dt)
    if to_dt is not None:
        q = q.where(SessionReport.started_at < to_dt)
    q = q.order_by(SessionReport.started_at.desc())
    rows = db.execute(q).scalars().all()
    out = [_to_out(r) for r in rows]
    logger.info(
        "GET /reports from=%s to=%s timezone=%s -> %d reports",
        from_date,
        to_date,
        tz,
        len(out),
    )
    if out:
        logger.info("GET /reports sample struct: %s", json.dumps(out[0], default=str))
    return out


@router.delete("", response_model=dict)
def delete_all_reports(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """Delete all reports for the current user."""
    result = db.execute(delete(SessionReport).where(SessionReport.user_id == user_id))
    db.commit()
    n = result.rowcount
    logger.info("DELETE /reports user_id=%s -> %d deleted", user_id, n)
    return {"deleted": n}


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    r = db.execute(
        select(SessionReport).where(
            SessionReport.id == report_id,
            SessionReport.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_out(r)
