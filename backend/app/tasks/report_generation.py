"""Celery task for weekly report generation.

Produces a comprehensive performance report for a tenant over a specified
week period.  The report covers team-level aggregates, per-agent breakdowns,
quality parameter trends, top calls, and hot leads.

Usage::

    from app.tasks.report_generation import generate_weekly_report

    generate_weekly_report.delay(
        tenant_id="<uuid>",
        week_start="2026-02-24",
        week_end="2026-03-02",
        generated_by="<user-uuid>",  # optional
    )
"""

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.report import ReportStatus, WeeklyReport
from app.services.reports.weekly_report import WeeklyReportGenerator
from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    """Create a synchronous database session for use within Celery tasks."""
    return SessionLocal()


def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously within a Celery worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Main task
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="app.tasks.report_generation.generate_weekly_report",
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=300,
    time_limit=600,
)
def generate_weekly_report(
    self: Any,
    tenant_id: str,
    week_start: str,
    week_end: str,
    generated_by: Optional[str] = None,
    report_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a weekly performance report for a tenant.

    Parameters
    ----------
    tenant_id:
        UUID string of the tenant to generate the report for.
    week_start:
        Start date of the reporting week in ISO format (``YYYY-MM-DD``).
    week_end:
        End date of the reporting week in ISO format (``YYYY-MM-DD``).
    generated_by:
        Optional UUID string of the user who triggered the report.
    report_id:
        Optional UUID string of a pre-created ``WeeklyReport`` record.
        If not provided, a new record will be created.

    Returns
    -------
    dict
        Summary of the generation result including the report ID and status.
    """
    db: Session = _get_sync_session()

    try:
        # ── Parse inputs ──────────────────────────────────────────────
        tid = uuid.UUID(tenant_id)
        ws = date.fromisoformat(week_start)
        we = date.fromisoformat(week_end)

        if ws > we:
            raise ValueError(
                f"week_start ({week_start}) must be before week_end ({week_end})"
            )

        generated_by_uuid: Optional[uuid.UUID] = None
        if generated_by:
            generated_by_uuid = uuid.UUID(generated_by)

        # ── Get or create report record ───────────────────────────────
        report_record = _get_or_create_report(
            db=db,
            report_id=report_id,
            tenant_id=tid,
            week_start=ws,
            week_end=we,
            generated_by=generated_by_uuid,
        )

        # Mark as generating
        report_record.status = ReportStatus.generating
        report_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Generating weekly report %s for tenant=%s (%s to %s)",
            report_record.id,
            tenant_id,
            week_start,
            week_end,
        )

        # ── Generate the report data ──────────────────────────────────
        generator = WeeklyReportGenerator(db)

        # The generator's generate method is async (linter-created version),
        # so we run it through the async bridge.
        report_data = _run_async(
            generator.generate(
                tenant_id=tid,
                week_start=ws,
                week_end=we,
            )
        )

        # ── Save results ──────────────────────────────────────────────
        report_record.report_data = report_data
        report_record.status = ReportStatus.completed
        report_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Weekly report %s completed — %d total calls, avg_score=%.1f",
            report_record.id,
            report_data.get("summary", {}).get("total_calls", 0),
            report_data.get("summary", {}).get("avg_quality_score", 0),
        )

        return {
            "status": "completed",
            "report_id": str(report_record.id),
            "tenant_id": tenant_id,
            "week_start": week_start,
            "week_end": week_end,
            "total_calls": report_data.get("summary", {}).get("total_calls", 0),
        }

    except Exception as exc:
        logger.exception(
            "Weekly report generation failed for tenant=%s: %s",
            tenant_id,
            exc,
        )

        # Try to mark the report record as failed
        _mark_report_failed(db, report_id, str(exc))

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "week_start": week_start,
            "week_end": week_end,
            "error": str(exc),
        }

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_create_report(
    db: Session,
    report_id: Optional[str],
    tenant_id: uuid.UUID,
    week_start: date,
    week_end: date,
    generated_by: Optional[uuid.UUID],
) -> WeeklyReport:
    """Retrieve an existing report record or create a new one.

    If ``report_id`` is provided, attempts to load that record.  Otherwise,
    checks for an existing report covering the same week for the tenant.  If
    none exists, creates a new one.
    """
    # Try loading by explicit ID
    if report_id:
        try:
            rid = uuid.UUID(report_id)
            existing = (
                db.query(WeeklyReport).filter(WeeklyReport.id == rid).first()
            )
            if existing:
                return existing
        except (ValueError, TypeError):
            logger.warning("Invalid report_id format: %s", report_id)

    # Check for an existing report for this week
    existing = (
        db.query(WeeklyReport)
        .filter(
            WeeklyReport.tenant_id == tenant_id,
            WeeklyReport.week_start == week_start,
            WeeklyReport.week_end == week_end,
        )
        .first()
    )

    if existing:
        logger.info(
            "Found existing report %s for tenant=%s week=%s to %s",
            existing.id,
            tenant_id,
            week_start,
            week_end,
        )
        return existing

    # Create new record
    report = WeeklyReport(
        tenant_id=tenant_id,
        week_start=week_start,
        week_end=week_end,
        generated_by=generated_by,
        status=ReportStatus.pending,
    )
    db.add(report)
    db.flush()

    logger.info(
        "Created new weekly report %s for tenant=%s week=%s to %s",
        report.id,
        tenant_id,
        week_start,
        week_end,
    )

    return report


def _mark_report_failed(
    db: Session,
    report_id: Optional[str],
    error_message: str,
) -> None:
    """Mark a report record as failed."""
    if not report_id:
        return

    try:
        rid = uuid.UUID(report_id)
        report = (
            db.query(WeeklyReport).filter(WeeklyReport.id == rid).first()
        )
        if report:
            report.status = ReportStatus.failed
            report.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        logger.exception("Failed to mark report %s as failed", report_id)
        db.rollback()
