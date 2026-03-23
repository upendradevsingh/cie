from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.conversations import router as conversations_router
from app.api.extractions import router as extractions_router
from app.api.profiles import router as profiles_router
from app.api.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(conversations_router, prefix="/api/v1")
api_router.include_router(extractions_router, prefix="/api/v1")
api_router.include_router(profiles_router, prefix="/api/v1")
api_router.include_router(analytics_router, prefix="/api/v1")
