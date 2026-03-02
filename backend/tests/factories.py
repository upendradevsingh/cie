"""Test data factories for SalesLens.

Provides helper functions to create test entities (tenants, users, calls, etc.)
with sensible defaults. Uses plain functions instead of factory_boy to keep
dependencies minimal.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.models.action_item import ActionItem, ActionUrgency
from app.models.call import Call, CallStatus, IntentClassification
from app.models.integration import Integration
from app.models.intent import CallIntentSignal, IntentSignal
from app.models.persona import CallPersona, PersonaType
from app.models.quality import CallQualityScore, QualityParameter
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.auth import hash_password


def create_tenant(
    db: Any,
    name: str = "Test Corp",
    slug: str = "test-corp",
    **kwargs: Any,
) -> Tenant:
    """Create and persist a Tenant."""
    tenant = Tenant(
        name=name,
        slug=slug,
        is_active=kwargs.get("is_active", True),
        settings=kwargs.get("settings"),
    )
    db.add(tenant)
    db.flush()
    return tenant


def create_user(
    db: Any,
    tenant: Tenant,
    email: str = "agent@test.com",
    full_name: str = "Test Agent",
    role: UserRole = UserRole.agent,
    password: str = "testpassword123",
    **kwargs: Any,
) -> User:
    """Create and persist a User."""
    user = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=kwargs.get("is_active", True),
    )
    db.add(user)
    db.flush()
    return user


def create_admin(
    db: Any,
    tenant: Tenant,
    email: str = "admin@test.com",
    full_name: str = "Test Admin",
    password: str = "adminpassword123",
    **kwargs: Any,
) -> User:
    """Create and persist an admin User."""
    return create_user(
        db,
        tenant,
        email=email,
        full_name=full_name,
        role=UserRole.admin,
        password=password,
        **kwargs,
    )


def create_call(
    db: Any,
    tenant: Tenant,
    agent: Optional[User] = None,
    status: CallStatus = CallStatus.uploaded,
    overall_score: Optional[float] = None,
    intent_classification: Optional[IntentClassification] = None,
    lead_intent_score: Optional[float] = None,
    **kwargs: Any,
) -> Call:
    """Create and persist a Call."""
    call = Call(
        tenant_id=tenant.id,
        agent_id=agent.id if agent else None,
        status=status,
        overall_score=overall_score,
        lead_intent_score=lead_intent_score,
        intent_classification=intent_classification,
        recording_file_path=kwargs.get("recording_file_path"),
        recording_url=kwargs.get("recording_url"),
        transcript_raw=kwargs.get("transcript_raw"),
        transcript_segments=kwargs.get("transcript_segments"),
        analysis=kwargs.get("analysis"),
        lead_id=kwargs.get("lead_id"),
        lead_name=kwargs.get("lead_name"),
        lead_phone=kwargs.get("lead_phone"),
        source=kwargs.get("source"),
        language=kwargs.get("language", "en"),
        duration_seconds=kwargs.get("duration_seconds"),
        custom_fields=kwargs.get("custom_fields"),
    )
    db.add(call)
    db.flush()
    return call


def create_quality_parameter(
    db: Any,
    tenant: Tenant,
    name: str = "Opening & Greeting",
    description: str = "Proper introduction and energy",
    weight: float = 1.0,
    category: str = "Communication",
    **kwargs: Any,
) -> QualityParameter:
    """Create and persist a QualityParameter."""
    param = QualityParameter(
        tenant_id=tenant.id,
        name=name,
        description=description,
        weight=weight,
        category=category,
        is_active=kwargs.get("is_active", True),
        display_order=kwargs.get("display_order", 0),
    )
    db.add(param)
    db.flush()
    return param


def create_intent_signal(
    db: Any,
    tenant: Tenant,
    name: str = "Budget Mentioned",
    description: str = "Customer mentioned or confirmed budget",
    **kwargs: Any,
) -> IntentSignal:
    """Create and persist an IntentSignal."""
    signal = IntentSignal(
        tenant_id=tenant.id,
        name=name,
        description=description,
        is_active=kwargs.get("is_active", True),
    )
    db.add(signal)
    db.flush()
    return signal


def create_persona_type(
    db: Any,
    tenant: Tenant,
    name: str = "Ready Buyer",
    description: str = "High intent buyer ready to purchase",
    **kwargs: Any,
) -> PersonaType:
    """Create and persist a PersonaType."""
    ptype = PersonaType(
        tenant_id=tenant.id,
        name=name,
        description=description,
        bant_profile=kwargs.get("bant_profile"),
        is_active=kwargs.get("is_active", True),
    )
    db.add(ptype)
    db.flush()
    return ptype


def create_integration(
    db: Any,
    tenant: Tenant,
    name: str = "Test Webhook",
    integration_type: str = "webhook",
    config: Optional[Dict] = None,
    **kwargs: Any,
) -> Integration:
    """Create and persist an Integration."""
    integration = Integration(
        tenant_id=tenant.id,
        name=name,
        type=integration_type,
        config=config or {"url": "https://example.com/webhook"},
        is_active=kwargs.get("is_active", True),
    )
    db.add(integration)
    db.flush()
    return integration


def create_call_quality_score(
    db: Any,
    call: Call,
    parameter: QualityParameter,
    score: float = 7.0,
    justification: str = "Good performance",
) -> CallQualityScore:
    """Create and persist a CallQualityScore."""
    cqs = CallQualityScore(
        call_id=call.id,
        parameter_id=parameter.id,
        score=score,
        justification=justification,
    )
    db.add(cqs)
    db.flush()
    return cqs


def create_default_quality_parameters(db: Any, tenant: Tenant) -> list:
    """Create a standard set of quality parameters for testing."""
    params_data = [
        ("Opening & Greeting", "Proper introduction and energy", 1.0, "Communication"),
        ("Need Discovery", "Asked probing questions", 1.0, "Discovery"),
        ("Product Knowledge", "Accurate info and features", 1.0, "Knowledge"),
        ("Objection Handling", "Addressed concerns and rebuttals", 1.0, "Objection"),
        ("Pricing Discussion", "Transparent and value-framed", 1.0, "Pricing"),
        ("Urgency Creation", "Time-sensitive offers", 0.8, "Closing"),
        ("Next Steps", "Clear action items and follow-up", 1.0, "Closing"),
        ("Call Control", "Managed conversation flow", 0.8, "Communication"),
        ("Active Listening", "Acknowledged and paraphrased", 0.8, "Communication"),
        ("Closing Technique", "Asked for commitment", 1.0, "Closing"),
    ]
    params = []
    for i, (name, desc, weight, category) in enumerate(params_data):
        params.append(
            create_quality_parameter(
                db, tenant, name=name, description=desc,
                weight=weight, category=category, display_order=i,
            )
        )
    return params


def create_default_intent_signals(db: Any, tenant: Tenant) -> list:
    """Create a standard set of intent signals for testing."""
    signals_data = [
        ("Budget Mentioned", "Customer mentioned or confirmed budget"),
        ("Timeline Discussed", "Customer discussed timeline or deadline"),
        ("Decision Maker Identified", "Key decision maker identified"),
        ("Competitor Comparison", "Competitor mentioned or compared"),
        ("Specific Requirements Stated", "Customer stated specific needs"),
        ("Follow-up Requested", "Customer or agent requested follow-up"),
        ("Pricing Asked", "Customer asked about pricing"),
        ("Objections Raised", "Customer raised objections"),
    ]
    signals = []
    for name, desc in signals_data:
        signals.append(create_intent_signal(db, tenant, name=name, description=desc))
    return signals
