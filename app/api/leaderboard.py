"""Leaderboard API (publish, list, react)."""
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id, get_optional_user_id
from app.core.database import get_db
from app.models.session_report import SessionReport
from app.models.reaction import Reaction
from app.models.user import User
from app.api.reports import _to_out

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
    user_name: str | None
    user_email: str | None
    username: str | None
    is_own_report: bool  # Whether this report belongs to the current user
    reactions: dict[str, int]  # emoji -> count
    user_reaction: str | None  # emoji that current user reacted with, if any


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
):
    """Get leaderboard of published reports, sorted by zone_in_score descending. Works without authentication."""
    # Get all published reports with user info, ordered by zone_in_score descending
    query = (
        select(SessionReport, User.name, User.email, User.username)
        .join(User, SessionReport.user_id == User.id)
        .where(SessionReport.published == True)
        .order_by(SessionReport.zone_in_score.desc(), SessionReport.created_at.desc())
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
    for report, user_name, user_email, username in results:
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
        entries.append(LeaderboardEntry(
            **report_dict,
            user_name=user_name,
            user_email=user_email,
            username=username,
            is_own_report=is_own_report,
            reactions=reaction_counts,
            user_reaction=user_reaction,
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
    is_own_profile: bool  # Whether this is the current user's profile


@router.get("/lifetime", response_model=list[LifetimeLeaderboardEntry])
def get_lifetime_leaderboard(
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get leaderboard of users sorted by their lifetime maximum ZoneIn score. Works without authentication."""
    # Get all users with max_zone_in_score, ordered by max_zone_in_score descending
    query = (
        select(User)
        .where(User.max_zone_in_score.isnot(None))
        .order_by(User.max_zone_in_score.desc(), User.created_at.asc())
    )
    
    users = db.execute(query).scalars().all()
    
    # Build response
    entries = []
    for user in users:
        is_own_profile = user_id is not None and user.id == user_id
        
        entries.append(LifetimeLeaderboardEntry(
            user_id=str(user.id),
            user_name=user.name,
            user_email=user.email,
            username=user.username,
            max_zone_in_score=user.max_zone_in_score,
            is_own_profile=is_own_profile,
        ))
    
    logger.info("GET /leaderboard/lifetime -> %d entries", len(entries))
    return entries
