"""Leaderboard API (publish, list, react)."""
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, nulls_last
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id, get_optional_user_id
from app.core.avatar import default_avatar_url_for_user
from app.core.database import get_db
from app.models.session_report import SessionReport
from app.models.reaction import Reaction
from app.models.user import User
from app.api.reports import _to_out, _top_focus_app_from_segments

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class PublishResponse(BaseModel):
    published: bool


class LeaderboardEntry(BaseModel):
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
    timeline_buckets_json: str | None
    cloud_ai_enabled: bool
    created_at: datetime
    published: bool
    published_at: datetime | None = None  # When report was published (feed sort)
    user_name: str | None
    user_email: str | None
    username: str | None
    avatar_url: str | None = None  # Profile picture URL (or default)
    is_own_report: bool  # Whether this report belongs to the current user
    reactions: dict[str, int]  # emoji -> count
    user_reaction: str | None  # emoji that current user reacted with, if any
    top_focus_app: str | None = None  # Most used app during focused time


class ReactRequest(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=10, description="Emoji string (e.g., '👏', '🔥')")


class ReactResponse(BaseModel):
    emoji: str
    count: int


# Allowed emojis
ALLOWED_EMOJIS = ["👏", "🔥", "💪", "⭐", "🎉"]


@router.post("/reports/{report_id}/publish", response_model=PublishResponse)
def publish_report(
    report_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """Publish a report to the leaderboard."""
    report = db.execute(
        select(SessionReport).where(
            SessionReport.id == report_id,
            SessionReport.user_id == user_id,
        )
    ).scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.published = True
    # Keep original published_at on republish so feed order is preserved
    if report.published_at is None:
        report.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    
    logger.info("Report published: report_id=%s user_id=%s", report_id, user_id)
    return {"published": True}


@router.post("/reports/{report_id}/unpublish", response_model=PublishResponse)
def unpublish_report(
    report_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """Unpublish a report from the leaderboard."""
    report = db.execute(
        select(SessionReport).where(
            SessionReport.id == report_id,
            SessionReport.user_id == user_id,
        )
    ).scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.published = False
    db.commit()
    db.refresh(report)
    
    logger.info("Report unpublished: report_id=%s user_id=%s", report_id, user_id)
    return {"published": False}


@router.get("", response_model=list[LeaderboardEntry])
def get_leaderboard(
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)],
    db: Annotated[Session, Depends(get_db)],
    tz: str | None = Query(None, alias="timezone", description="IANA timezone e.g. America/New_York"),
    sort: str = Query("focus", description="Sort order: 'focus' = highest focus time first (leaderboard), 'recent' = most recent posted first (published reports)"),
):
    """Get published reports. sort=focus (default) = by focused_sec desc; sort=recent = by published_at desc (when you published). Works without authentication."""
    order_by = (
        nulls_last(SessionReport.published_at.desc())
        if sort == "recent"
        else (SessionReport.focused_sec.desc(), SessionReport.created_at.desc())
    )
    query = (
        select(SessionReport, User.name, User.email, User.username, User.avatar_url)
        .join(User, SessionReport.user_id == User.id)
        .where(SessionReport.published == True)
        .order_by(*order_by if isinstance(order_by, tuple) else (order_by,))
    )
    
    results = db.execute(query).all()
    
    # Get all reactions for these reports
    report_ids = [r[0].id for r in results]
    reactions_query = select(Reaction).where(Reaction.report_id.in_(report_ids))
    all_reactions = db.execute(reactions_query).scalars().all()
    
    # Group reactions by report_id and emoji
    reactions_by_report: dict[UUID, dict[str, list[UUID]]] = {}
    for reaction in all_reactions:
        if reaction.report_id not in reactions_by_report:
            reactions_by_report[reaction.report_id] = {}
        if reaction.emoji not in reactions_by_report[reaction.report_id]:
            reactions_by_report[reaction.report_id][reaction.emoji] = []
        reactions_by_report[reaction.report_id][reaction.emoji].append(reaction.user_id)
    
    # Build response
    entries = []
    for report, user_name, user_email, username, avatar_url in results:
        # Check if this is the current user's report (only if authenticated)
        is_own_report = user_id is not None and report.user_id == user_id
        
        # Get reaction counts for this report
        report_reactions = reactions_by_report.get(report.id, {})
        reaction_counts = {emoji: len(user_ids) for emoji, user_ids in report_reactions.items()}
        
        # Get current user's reaction (only if authenticated)
        user_reaction = None
        if user_id is not None:
            for emoji, user_ids in report_reactions.items():
                if user_id in user_ids:
                    user_reaction = emoji
                    break
        
        report_dict = _to_out(report, tz)
        top_focus_app = _top_focus_app_from_segments(getattr(report, "half_focused_segments_json", None))
        effective_avatar = avatar_url or default_avatar_url_for_user(report.user_id)
        entries.append(LeaderboardEntry(
            **report_dict,
            user_name=user_name,
            user_email=user_email,
            username=username,
            avatar_url=effective_avatar,
            is_own_report=is_own_report,
            reactions=reaction_counts,
            user_reaction=user_reaction,
            top_focus_app=top_focus_app,
        ))
    
    logger.info("GET /leaderboard -> %d entries", len(entries))
    return entries


@router.post("/reports/{report_id}/react", response_model=ReactResponse)
def react_to_report(
    report_id: UUID,
    body: ReactRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """Add or update a reaction to a published report. Users can only react once per report."""
    # Validate emoji
    if body.emoji not in ALLOWED_EMOJIS:
        raise HTTPException(
            status_code=400,
            detail=f"Emoji must be one of: {', '.join(ALLOWED_EMOJIS)}"
        )
    
    # Check if report exists and is published
    report = db.execute(
        select(SessionReport).where(SessionReport.id == report_id)
    ).scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not report.published:
        raise HTTPException(status_code=400, detail="Report is not published")
    
    # Check if user already reacted
    existing_reaction = db.execute(
        select(Reaction).where(
            Reaction.user_id == user_id,
            Reaction.report_id == report_id,
        )
    ).scalar_one_or_none()
    
    if existing_reaction:
        # Update existing reaction
        existing_reaction.emoji = body.emoji
        db.commit()
        db.refresh(existing_reaction)
    else:
        # Create new reaction
        reaction = Reaction(
            user_id=user_id,
            report_id=report_id,
            emoji=body.emoji,
        )
        db.add(reaction)
        db.commit()
        db.refresh(reaction)
    
    # Get count of reactions with this emoji for this report
    count = db.execute(
        select(func.count(Reaction.id))
        .where(Reaction.report_id == report_id, Reaction.emoji == body.emoji)
    ).scalar_one()
    
    logger.info("Reaction added/updated: report_id=%s user_id=%s emoji=%s count=%d", 
                report_id, user_id, body.emoji, count)
    return ReactResponse(emoji=body.emoji, count=count)


@router.delete("/reports/{report_id}/react")
def remove_reaction(
    report_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove user's reaction from a report."""
    reaction = db.execute(
        select(Reaction).where(
            Reaction.user_id == user_id,
            Reaction.report_id == report_id,
        )
    ).scalar_one_or_none()
    
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    
    db.delete(reaction)
    db.commit()
    
    logger.info("Reaction removed: report_id=%s user_id=%s", report_id, user_id)
    return {"removed": True}


class LifetimeLeaderboardEntry(BaseModel):
    model_config = {"from_attributes": True}

    user_id: str
    user_name: str | None
    user_email: str | None
    username: str | None
    max_zone_in_score: float | None
    total_focused_sec: float  # Sum of focused_sec across all reports (for ZoneIn Focus Minutes)
    is_own_profile: bool  # Whether this is the current user's profile


@router.get("/lifetime", response_model=list[LifetimeLeaderboardEntry])
def get_lifetime_leaderboard(
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get leaderboard of users sorted by total focused time (ZoneIn Focus Minutes). Uses stored total_focused_sec when set, else sum from reports."""
    total_focused = (
        select(SessionReport.user_id, func.sum(SessionReport.focused_sec).label("total_focused_sec"))
        .group_by(SessionReport.user_id)
    ).subquery()
    query = (
        select(User, total_focused.c.total_focused_sec)
        .join(total_focused, User.id == total_focused.c.user_id)
        .order_by(
            func.coalesce(User.total_focused_sec, total_focused.c.total_focused_sec).desc(),
            User.created_at.asc(),
        )
    )
    results = db.execute(query).all()
    entries = []
    for user, sum_focused in results:
        is_own_profile = user_id is not None and user.id == user_id
        # Prefer stored total on user (updated on report create/update), fallback to sum from reports
        total_sec = getattr(user, "total_focused_sec", None)
        if total_sec is None:
            total_sec = float(sum_focused or 0)
        else:
            total_sec = float(total_sec)
        entries.append(LifetimeLeaderboardEntry(
            user_id=str(user.id),
            user_name=user.name,
            user_email=user.email,
            username=user.username,
            avatar_url=getattr(user, "avatar_url", None) or default_avatar_url_for_user(user.id),
            max_zone_in_score=user.max_zone_in_score,
            total_focused_sec=total_sec,
            is_own_profile=is_own_profile,
        ))
    logger.info("GET /leaderboard/lifetime -> %d entries", len(entries))
    return entries
