"""LLM-based call analysis service package.

Provides the :class:`CallAnalyzer` class that takes a transcript and
configurable evaluation criteria, calls an LLM (OpenAI GPT-4o-mini by
default), and returns structured analysis results covering quality scores,
lead intelligence, persona identification, and action items.
"""

from app.services.analysis.llm_analyzer import AnalysisResult, CallAnalyzer

__all__ = ["CallAnalyzer", "AnalysisResult"]
