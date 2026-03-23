"""Correction analytics endpoints."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.session import get_db_with_tenant
from app.models.conversation import Conversation
from app.models.extraction import Extraction
from app.schemas.extraction import (
    CorrectionAnalyticsResponse,
    TypeCorrectionStats,
)
from app.services.auth import TokenClaims, get_token_claims

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/corrections", response_model=CorrectionAnalyticsResponse)
async def get_correction_analytics(
    days: int = Query(30, ge=1, le=365),
    profile_id: Optional[str] = None,
    claims: TokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db_with_tenant),
) -> CorrectionAnalyticsResponse:
    """Get correction rates and trends per extraction type.

    Trend is computed by comparing the correction rate in the recent half
    of the period vs the older half. >5% decrease = "improving",
    >5% increase = "degrading", otherwise "stable".
    """
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    midpoint = now - timedelta(days=days / 2)

    # Base query filter
    base_filter = [
        Extraction.tenant_id == claims.tenant_id,
        Extraction.created_at >= period_start,
    ]

    if profile_id:
        base_filter.extend([
            Extraction.conversation_id == Conversation.id,
            Conversation.profile_id == profile_id,
        ])

    # Full period stats by type
    query = db.query(
        Extraction.extraction_type,
        func.count(Extraction.id).label("total"),
        func.sum(
            case((Extraction.corrected == True, 1), else_=0)  # noqa: E712
        ).label("corrected"),
    ).filter(*base_filter)

    if profile_id:
        query = query.join(
            Conversation, Extraction.conversation_id == Conversation.id
        )

    full_stats = query.group_by(Extraction.extraction_type).all()

    # Older half stats (for trend computation)
    older_filter = base_filter + [Extraction.created_at < midpoint]
    older_query = db.query(
        Extraction.extraction_type,
        func.count(Extraction.id).label("total"),
        func.sum(
            case((Extraction.corrected == True, 1), else_=0)  # noqa: E712
        ).label("corrected"),
    ).filter(*older_filter)

    if profile_id:
        older_query = older_query.join(
            Conversation, Extraction.conversation_id == Conversation.id
        )

    older_stats = {
        row[0]: (row[1], row[2] or 0)
        for row in older_query.group_by(Extraction.extraction_type).all()
    }

    # Recent half stats
    recent_filter = base_filter + [Extraction.created_at >= midpoint]
    recent_query = db.query(
        Extraction.extraction_type,
        func.count(Extraction.id).label("total"),
        func.sum(
            case((Extraction.corrected == True, 1), else_=0)  # noqa: E712
        ).label("corrected"),
    ).filter(*recent_filter)

    if profile_id:
        recent_query = recent_query.join(
            Conversation, Extraction.conversation_id == Conversation.id
        )

    recent_stats = {
        row[0]: (row[1], row[2] or 0)
        for row in recent_query.group_by(Extraction.extraction_type).all()
    }

    # Build response
    by_type: dict[str, TypeCorrectionStats] = {}
    overall_total = 0
    overall_corrected = 0

    for ext_type, total, corrected in full_stats:
        corrected = corrected or 0
        rate = corrected / total if total > 0 else 0.0
        trend = _compute_trend(
            older_stats.get(ext_type, (0, 0)),
            recent_stats.get(ext_type, (0, 0)),
        )
        by_type[ext_type] = TypeCorrectionStats(
            total_extractions=total,
            corrected_count=corrected,
            correction_rate=round(rate, 4),
            trend=trend,
        )
        overall_total += total
        overall_corrected += corrected

    overall_rate = overall_corrected / overall_total if overall_total > 0 else 0.0
    overall_older = (
        sum(v[0] for v in older_stats.values()),
        sum(v[1] for v in older_stats.values()),
    )
    overall_recent = (
        sum(v[0] for v in recent_stats.values()),
        sum(v[1] for v in recent_stats.values()),
    )

    return CorrectionAnalyticsResponse(
        by_type=by_type,
        overall=TypeCorrectionStats(
            total_extractions=overall_total,
            corrected_count=overall_corrected,
            correction_rate=round(overall_rate, 4),
            trend=_compute_trend(overall_older, overall_recent),
        ),
        period_days=days,
    )


def _compute_trend(
    older: tuple[int, int],
    recent: tuple[int, int],
) -> str:
    """Compare correction rates between two periods.

    Args:
        older: (total_extractions, corrected_count) for older half
        recent: (total_extractions, corrected_count) for recent half

    Returns: "improving", "degrading", or "stable"
    """
    older_total, older_corrected = older
    recent_total, recent_corrected = recent

    older_rate = older_corrected / older_total if older_total > 0 else 0.0
    recent_rate = recent_corrected / recent_total if recent_total > 0 else 0.0

    diff = recent_rate - older_rate
    if diff < -0.05:
        return "improving"
    elif diff > 0.05:
        return "degrading"
    return "stable"
