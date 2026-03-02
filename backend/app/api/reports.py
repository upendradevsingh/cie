"""Weekly report generation and retrieval routes."""

from datetime import date, timedelta
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import get_db_with_tenant
from app.models.report import ReportStatus, WeeklyReport
from app.models.user import User
from app.schemas.report import WeeklyReportRequest, WeeklyReportResponse
from app.services.auth import get_current_active_user, require_role

router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# POST /reports/weekly
# ---------------------------------------------------------------------------


@router.post(
    "/weekly",
    response_model=WeeklyReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger weekly report generation",
)
def trigger_weekly_report(
    body: WeeklyReportRequest,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin", "team_lead"]))],
) -> WeeklyReportResponse:
    """Create a weekly report request and dispatch it for async generation.

    If ``week_end`` is not provided it defaults to ``week_start + 6 days``.
    A Celery task is dispatched to aggregate data and populate the report.
    Only admins and team leads can trigger report generation.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    week_start = body.week_start
    week_end = body.week_end or (week_start + timedelta(days=6))

    # Check for duplicate report
    existing = (
        db.query(WeeklyReport)
        .filter(
            # RLS enforces tenant isolation; filter kept as defense-in-depth
            WeeklyReport.tenant_id == current_user.tenant_id,
            WeeklyReport.week_start == week_start,
            WeeklyReport.week_end == week_end,
            WeeklyReport.status.in_([ReportStatus.pending, ReportStatus.generating, ReportStatus.completed]),
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A report for {week_start} to {week_end} already exists "
                f"(status: {existing.status.value})"
            ),
        )

    report = WeeklyReport(
        tenant_id=current_user.tenant_id,
        week_start=week_start,
        week_end=week_end,
        generated_by=current_user.id,
        status=ReportStatus.pending,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Dispatch async generation task
    try:
        from app.tasks.report_generation import generate_weekly_report

        generate_weekly_report.delay(
            str(current_user.tenant_id),
            str(report.week_start),
            str(report.week_end),
            str(current_user.id),
            str(report.id),
        )
    except ImportError:
        # Tasks module may not be available yet during development
        pass

    return WeeklyReportResponse(
        id=report.id,
        tenant_id=report.tenant_id,
        week_start=report.week_start,
        week_end=report.week_end,
        report_data=report.report_data or {},
        status=report.status.value if hasattr(report.status, "value") else str(report.status),
        created_at=report.created_at,
    )


# ---------------------------------------------------------------------------
# GET /reports/weekly
# ---------------------------------------------------------------------------


@router.get(
    "/weekly",
    response_model=List[WeeklyReportResponse],
    summary="List generated weekly reports",
)
def list_weekly_reports(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    report_status: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status: pending, generating, completed, failed",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
) -> List[WeeklyReportResponse]:
    """Return a paginated list of weekly reports for the current tenant.

    Optionally filter by generation status.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    query = db.query(WeeklyReport).filter(
        # RLS enforces tenant isolation; filter kept as defense-in-depth
        WeeklyReport.tenant_id == current_user.tenant_id,
    )

    if report_status:
        status_val = report_status.lower()
        valid_statuses = {s.value for s in ReportStatus}
        if status_val in valid_statuses:
            query = query.filter(WeeklyReport.status == ReportStatus(status_val))

    reports = (
        query.order_by(WeeklyReport.week_start.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [
        WeeklyReportResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            week_start=r.week_start,
            week_end=r.week_end,
            report_data=r.report_data or {},
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            created_at=r.created_at,
        )
        for r in reports
    ]


# ---------------------------------------------------------------------------
# GET /reports/weekly/{report_id}
# ---------------------------------------------------------------------------


@router.get(
    "/weekly/{report_id}",
    response_model=WeeklyReportResponse,
    summary="Get a specific weekly report",
)
def get_weekly_report(
    report_id: UUID,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> WeeklyReportResponse:
    """Return the full content of a specific weekly report.

    Returns **404** if the report does not exist or belongs to a different
    tenant.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    report = (
        db.query(WeeklyReport)
        .filter(
            WeeklyReport.id == report_id,
            # RLS enforces tenant isolation; filter kept as defense-in-depth
            WeeklyReport.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly report not found",
        )

    return WeeklyReportResponse(
        id=report.id,
        tenant_id=report.tenant_id,
        week_start=report.week_start,
        week_end=report.week_end,
        report_data=report.report_data or {},
        status=report.status.value if hasattr(report.status, "value") else str(report.status),
        created_at=report.created_at,
    )
