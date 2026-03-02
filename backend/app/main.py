"""SalesLens — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.db.session import SessionLocal, engine
from app.models.base import Base

# Import all models so Base.metadata knows about every table.
import app.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _recover_stuck_calls() -> None:
    """Re-queue calls stuck in non-terminal states after a restart.

    Looks for calls in ``uploaded``, ``transcribing``, or ``analyzing``
    status that haven't been updated in the last 30 minutes and
    re-dispatches them for processing.

    Uses ``FOR UPDATE SKIP LOCKED`` so that when multiple uvicorn workers
    start concurrently, each stuck call is only recovered once.
    """
    from app.models.call import Call, CallStatus

    db = SessionLocal()
    try:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        stuck_statuses = [
            CallStatus.uploaded,
            CallStatus.transcribing,
            CallStatus.analyzing,
        ]

        # Lock rows to prevent duplicate recovery across uvicorn workers.
        stuck_calls = (
            db.query(Call)
            .filter(
                Call.status.in_(stuck_statuses),
                Call.updated_at < threshold,
            )
            .with_for_update(skip_locked=True)
            .all()
        )

        if not stuck_calls:
            return

        logger.warning(
            "Found %d stuck call(s) — re-queuing for processing.", len(stuck_calls)
        )

        from app.tasks.call_processing import process_call

        for call in stuck_calls:
            old_status = call.status
            call.status = CallStatus.uploaded
            call.error_message = None
            call.updated_at = datetime.now(timezone.utc)
            db.flush()
            process_call.delay(str(call.id), tenant_id=str(call.tenant_id))
            logger.info("Re-queued stuck call %s (was %s)", call.id, old_status)

        db.commit()
    except Exception:
        logger.exception("Failed to recover stuck calls during startup.")
        db.rollback()
    finally:
        db.close()


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hook.

    On startup we ensure all tables exist (useful during development and
    first-run scenarios).  In production you should rely on Alembic
    migrations instead.
    """
    Base.metadata.create_all(bind=engine)
    _recover_stuck_calls()
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
