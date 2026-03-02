"""Report generation service package.

Provides the :class:`WeeklyReportGenerator` for creating periodic
performance reports aggregated across calls, agents, and teams.
"""

from app.services.reports.weekly_report import WeeklyReportGenerator

__all__ = ["WeeklyReportGenerator"]
