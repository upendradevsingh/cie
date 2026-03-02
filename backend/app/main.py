"""SalesLens — FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.db.session import engine
from app.models.base import Base

# Import all models so Base.metadata knows about every table.
import app.models  # noqa: F401


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hook.

    On startup we ensure all tables exist (useful during development and
    first-run scenarios).  In production you should rely on Alembic
    migrations instead.
    """
    Base.metadata.create_all(bind=engine)
    yield


# ── Application ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered sales call intelligence platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Return a simple health-check payload.

    Used by Docker HEALTHCHECK, load balancers, and uptime monitors.
    """
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.APP_VERSION}


# ── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["system"])
def root() -> dict:
    """Landing endpoint with basic application information."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tagline": "AI lens into every sales conversation",
        "docs": "/docs",
    }


# ── API Routes ──────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")
