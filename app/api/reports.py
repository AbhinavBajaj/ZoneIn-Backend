"""Session reports API (create, list, get)."""
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models.session_report import SessionReport
from app.models.user import User

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
        return _to_out(existing)

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
    return _to_out(r)


@router.get("", response_model=list[ReportOut])
def list_reports(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    q = select(SessionReport).where(SessionReport.user_id == user_id)
    if from_date is not None:
        q = q.where(SessionReport.started_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date is not None:
        q = q.where(SessionReport.ended_at <= datetime.combine(to_date, datetime.max.time()))
    q = q.order_by(SessionReport.started_at.desc())
    rows = db.execute(q).scalars().all()
    return [_to_out(r) for r in rows]


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
