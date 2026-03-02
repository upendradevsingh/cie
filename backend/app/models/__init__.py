"""SQLAlchemy models — import everything so Alembic and create_all() see them."""

from app.models.base import Base, TimestampMixin
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.call import Call, CallStatus, IntentClassification
from app.models.quality import CallQualityScore, QualityParameter
from app.models.intent import CallIntentSignal, IntentSignal
from app.models.persona import CallPersona, PersonaType
from app.models.action_item import ActionItem, ActionUrgency
from app.models.report import ReportStatus, WeeklyReport
from app.models.integration import ApiKey, Integration
from app.models.prompt_template import PromptTemplate

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Tenant
    "Tenant",
    # User
    "User",
    "UserRole",
    # Call
    "Call",
    "CallStatus",
    "IntentClassification",
    # Quality
    "QualityParameter",
    "CallQualityScore",
    # Intent
    "IntentSignal",
    "CallIntentSignal",
    # Persona
    "PersonaType",
    "CallPersona",
    # Action items
    "ActionItem",
    "ActionUrgency",
    # Reports
    "WeeklyReport",
    "ReportStatus",
    # Integrations
    "Integration",
    "ApiKey",
    # Prompt templates
    "PromptTemplate",
]
