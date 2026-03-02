"""Pydantic schemas for the SalesLens API.

All public schemas are re-exported here so that the rest of the application
can import them from a single location::

    from app.schemas import UserCreate, UserResponse, CallUpload
"""

# ── Auth ──────────────────────────────────────────────────────────────────
from app.schemas.auth import LoginRequest, Token, TokenData

# ── Users ─────────────────────────────────────────────────────────────────
from app.schemas.user import UserBase, UserCreate, UserResponse, UserUpdate

# ── Tenants ───────────────────────────────────────────────────────────────
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

# ── Calls ─────────────────────────────────────────────────────────────────
from app.schemas.call import (
    CallListFilters,
    CallListResponse,
    CallResponse,
    CallSummary,
    CallUpload,
    CallWebhook,
    TranscriptResponse,
    TranscriptSegment,
)

# ── Quality Parameters & Scores ──────────────────────────────────────────
from app.schemas.quality import (
    CallQualityScoreResponse,
    QAOverride,
    QAOverrideItem,
    QualityParameterCreate,
    QualityParameterResponse,
    QualityParameterUpdate,
)

# ── Intent Signals ────────────────────────────────────────────────────────
from app.schemas.intent import (
    CallIntentResponse,
    IntentSignalCreate,
    IntentSignalResponse,
    IntentSignalUpdate,
)

# ── Persona Types & BANT ─────────────────────────────────────────────────
from app.schemas.persona import (
    CallPersonaResponse,
    PersonaTypeCreate,
    PersonaTypeResponse,
    PersonaTypeUpdate,
)

# ── Action Items ──────────────────────────────────────────────────────────
from app.schemas.action_item import ActionItemResponse, ActionItemUpdate

# ── Reports ───────────────────────────────────────────────────────────────
from app.schemas.report import WeeklyReportRequest, WeeklyReportResponse

# ── Integrations & API Keys ──────────────────────────────────────────────
from app.schemas.integration import (
    ApiKeyCreate,
    ApiKeyListResponse,
    ApiKeyResponse,
    IntegrationCreate,
    IntegrationResponse,
    IntegrationUpdate,
)

# ── Analytics & Leaderboard ──────────────────────────────────────────────
from app.schemas.analytics import (
    AgentAnalytics,
    LeaderboardEntry,
    TeamAnalytics,
    TrendData,
)

__all__ = [
    # Auth
    "TokenData",
    "Token",
    "LoginRequest",
    # Users
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Tenants
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    # Calls
    "CallUpload",
    "CallWebhook",
    "CallListFilters",
    "CallResponse",
    "CallListResponse",
    "CallSummary",
    "TranscriptSegment",
    "TranscriptResponse",
    # Quality
    "QualityParameterCreate",
    "QualityParameterUpdate",
    "QualityParameterResponse",
    "CallQualityScoreResponse",
    "QAOverrideItem",
    "QAOverride",
    # Intent
    "IntentSignalCreate",
    "IntentSignalUpdate",
    "IntentSignalResponse",
    "CallIntentResponse",
    # Persona
    "PersonaTypeCreate",
    "PersonaTypeUpdate",
    "PersonaTypeResponse",
    "CallPersonaResponse",
    # Action Items
    "ActionItemResponse",
    "ActionItemUpdate",
    # Reports
    "WeeklyReportRequest",
    "WeeklyReportResponse",
    # Integrations
    "IntegrationCreate",
    "IntegrationUpdate",
    "IntegrationResponse",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyListResponse",
    # Analytics
    "TeamAnalytics",
    "AgentAnalytics",
    "TrendData",
    "LeaderboardEntry",
]
