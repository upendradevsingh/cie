"""Celery application and task auto-discovery for SalesLens.

This module configures the Celery app instance used by all asynchronous
background tasks (call processing, report generation, etc.).  The broker
and result backend both use Redis, configured via ``settings.REDIS_URL``.

Worker startup::

    celery -A app.tasks worker --loglevel=info

Beat scheduler (for periodic tasks)::

    celery -A app.tasks beat --loglevel=info
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "saleslens",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    # Serialisation — JSON-only for security and debuggability.
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Time zone
    timezone="UTC",
    enable_utc=True,

    # Reliability settings
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Result expiry — keep results for 24 hours.
    result_expires=86400,

    # Task routing — all tasks go to the default queue unless overridden.
    task_default_queue="saleslens",
    task_default_exchange="saleslens",
    task_default_routing_key="saleslens",

    # Task soft/hard time limits (seconds).
    # Transcription + LLM analysis can take a while for long calls.
    task_soft_time_limit=600,   # 10 minutes soft limit
    task_time_limit=900,        # 15 minutes hard limit

    # Periodic tasks (Celery Beat schedule).
    # Can be extended with report scheduling, etc.
    beat_schedule={},
)

# Auto-discover task modules within the app.tasks package.
celery_app.autodiscover_tasks(["app.tasks"])

# Explicit imports to ensure tasks are registered with the worker.
import app.tasks.call_processing  # noqa: F401, E402
import app.tasks.report_generation  # noqa: F401, E402
