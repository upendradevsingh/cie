"""Analytics and leaderboard schemas."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Trend / time-series
# ---------------------------------------------------------------------------


class TrendData(BaseModel):
    """A single data point in a time-series trend."""

    date: str = Field(
        ...,
        description="Date or datetime label (ISO-8601 string, e.g. '2026-03-01')",
    )
    value: float = Field(..., description="Numeric value for this data point")
    label: str = Field(
        default="",
        description="Human-readable label for the series (e.g. 'Avg Quality Score')",
    )


# ---------------------------------------------------------------------------
# Team-level analytics  (matches frontend TeamAnalytics interface)
# ---------------------------------------------------------------------------


class DashboardStats(BaseModel):
    """Top-level KPI cards on the dashboard."""

    calls_today: int = Field(default=0, ge=0)
    calls_today_change: float = Field(default=0)
    avg_quality_score: float = Field(default=0)
    avg_quality_change: float = Field(default=0)
    hot_leads_count: int = Field(default=0, ge=0)
    hot_leads_change: float = Field(default=0)
    team_performance: float = Field(default=0)
    team_performance_change: float = Field(default=0)


class CallTrend(BaseModel):
    """A single data point for the call trend chart."""

    date: str
    count: int = 0
    avg_score: float = 0


class ScoreDistribution(BaseModel):
    """Score distribution bucket."""

    range: str
    count: int = 0


class HotLeadItem(BaseModel):
    """A hot lead entry for the dashboard."""

    call_id: str
    lead_name: str = ""
    lead_phone: str = ""
    intent_score: float = 0
    agent_name: str = ""
    created_at: str = ""


class CallListItemResponse(BaseModel):
    """Minimal call info for the recent calls list."""

    id: str
    agent_name: str = ""
    agent_id: str = ""
    lead_name: str = ""
    lead_id: str = ""
    lead_phone: str = ""
    duration: int = 0
    overall_score: float = 0
    intent_classification: str = "cold"
    intent_score: float = 0
    status: str = "uploaded"
    source: str = ""
    follow_up_urgency: Optional[str] = None
    created_at: str = ""


class TeamAnalytics(BaseModel):
    """Aggregated analytics across the entire team / tenant.

    Structure matches the frontend TeamAnalytics TypeScript interface.
    """

    stats: DashboardStats = Field(default_factory=DashboardStats)
    call_trends: List[CallTrend] = Field(default_factory=list)
    score_distribution: List[ScoreDistribution] = Field(default_factory=list)
    hot_leads: List[HotLeadItem] = Field(default_factory=list)
    recent_calls: List[CallListItemResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-agent analytics
# ---------------------------------------------------------------------------


class AgentAnalytics(BaseModel):
    """Performance analytics for a single agent."""

    agent_id: UUID
    agent_name: str
    total_calls: int = Field(..., ge=0)
    avg_quality_score: Optional[float] = Field(
        default=None,
        description="Average overall quality score (0–100)",
    )
    avg_intent_score: Optional[float] = Field(
        default=None,
        description="Average lead intent score (0–100)",
    )
    score_trend: List[TrendData] = Field(
        default_factory=list,
        description="Quality score over time",
    )
    top_parameters: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Parameters where this agent scores highest — "
            "each entry has parameter_name, avg_score"
        ),
    )
    areas_for_improvement: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Parameters where this agent scores lowest — "
            "each entry has parameter_name, avg_score"
        ),
    )


# ---------------------------------------------------------------------------
# Full analytics (matches frontend AnalyticsData interface)
# ---------------------------------------------------------------------------


class ConversionFunnelStage(BaseModel):
    """Single stage in the conversion funnel."""

    stage: str
    count: int = 0


class ParameterTrend(BaseModel):
    """Quality parameter comparison between current and previous period."""

    parameter_name: str
    current_avg: float = 0
    previous_avg: float = 0
    change: float = 0


class LeadClassificationItem(BaseModel):
    """Lead classification count."""

    classification: str
    count: int = 0


class AgentComparisonItem(BaseModel):
    """Agent data for the comparison chart."""

    agent_id: str
    agent_name: str
    total_calls: int = 0
    avg_quality_score: float = 0
    avg_intent_score: float = 0
    hot_leads_count: int = 0
    improvement_trend: float = 0
    quality_trend: List[CallTrend] = Field(default_factory=list)
    parameter_averages: List[Dict[str, Any]] = Field(default_factory=list)
    intent_breakdown: Dict[str, int] = Field(
        default_factory=lambda: {"hot": 0, "warm": 0, "cold": 0},
    )
    improvement_areas: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)


class AnalyticsDataResponse(BaseModel):
    """Full analytics data matching frontend AnalyticsData interface."""

    call_volume: List[CallTrend] = Field(default_factory=list)
    avg_quality_trend: List[CallTrend] = Field(default_factory=list)
    conversion_funnel: List[ConversionFunnelStage] = Field(default_factory=list)
    agent_comparison: List[AgentComparisonItem] = Field(default_factory=list)
    parameter_trends: List[ParameterTrend] = Field(default_factory=list)
    lead_classification: List[LeadClassificationItem] = Field(default_factory=list)
    score_distribution: List[ScoreDistribution] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


class LeaderboardEntry(BaseModel):
    """A single row on the agent leaderboard."""

    agent_id: UUID
    agent_name: str
    total_calls: int = Field(..., ge=0)
    avg_quality_score: Optional[float] = Field(
        default=None,
        description="Average overall quality score (0–100)",
    )
    avg_intent_score: Optional[float] = Field(
        default=None,
        description="Average lead intent score (0–100)",
    )
    hot_leads_count: int = Field(default=0, ge=0)
    rank: int = Field(..., ge=1, description="Leaderboard position (1 = best)")
