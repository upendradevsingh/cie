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
# Team-level analytics
# ---------------------------------------------------------------------------


class TeamAnalytics(BaseModel):
    """Aggregated analytics across the entire team / tenant."""

    total_calls: int = Field(..., ge=0, description="Total calls in the period")
    avg_quality_score: Optional[float] = Field(
        default=None,
        description="Average overall quality score (0–100)",
    )
    hot_leads_count: int = Field(
        default=0,
        ge=0,
        description="Number of calls classified as 'hot' intent",
    )
    warm_leads_count: int = Field(
        default=0,
        ge=0,
        description="Number of calls classified as 'warm' intent",
    )
    cold_leads_count: int = Field(
        default=0,
        ge=0,
        description="Number of calls classified as 'cold' intent",
    )
    calls_by_day: List[TrendData] = Field(
        default_factory=list,
        description="Call volume per day over the period",
    )
    top_agents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Top-performing agents — each entry has agent_id, agent_name, "
            "avg_quality_score, total_calls"
        ),
    )
    score_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Distribution of overall scores bucketed into ranges "
            "(e.g. {'0-20': 3, '21-40': 12, ...})"
        ),
    )


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
