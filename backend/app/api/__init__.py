"""API route package -- assembles all sub-routers into a single ``api_router``.

The main FastAPI application mounts ``api_router`` under the ``/api/v1``
prefix, giving every endpoint a URL like ``/api/v1/auth/login``,
``/api/v1/calls/upload``, etc.
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.calls import router as calls_router
from app.api.quality import router as quality_router
from app.api.intent import router as intent_router
from app.api.personas import router as personas_router
from app.api.analytics import router as analytics_router
from app.api.reports import router as reports_router
from app.api.users import agents_router, router as users_router
from app.api.integrations import router as integrations_router
from app.api.prompt_templates import router as prompt_templates_router

api_router = APIRouter()

# Authentication (no auth required for login/register/tenant)
api_router.include_router(auth_router)

# Core call management
api_router.include_router(calls_router)

# Configuration CRUD
api_router.include_router(quality_router)
api_router.include_router(intent_router)
api_router.include_router(personas_router)

# Analytics and reporting
api_router.include_router(analytics_router)
api_router.include_router(reports_router)

# User and tenant management
api_router.include_router(users_router)
api_router.include_router(agents_router)

# Integrations and API keys
api_router.include_router(integrations_router)

# Prompt templates
api_router.include_router(prompt_templates_router)
