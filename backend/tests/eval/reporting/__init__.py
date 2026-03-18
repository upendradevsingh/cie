"""Eval reporting package — diagnostic reports and delta tracking."""

from tests.eval.reporting.eval_report import generate_report
from tests.eval.reporting.delta_tracker import save_run, get_previous_metrics

__all__ = ["generate_report", "save_run", "get_previous_metrics"]
