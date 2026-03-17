"""Profile-driven extraction engine using OpenAI LLM."""
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.profiles import ExtractionProfile
from app.services.extraction.prompts import SYSTEM_PROMPT, build_extraction_prompt

logger = logging.getLogger(__name__)


@dataclass
class ExtractedItem:
    extraction_type: str
    description: str
    confidence: float
    attributed_to: Optional[dict] = None
    evidence: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    extractions: list[ExtractedItem]
    summary: str
    model_used: str
    tokens_used: int
    duration_ms: int


class ExtractionEngine:
    """Profile-driven extraction using LLM.

    Reads profile YAML → builds dynamic prompt → calls LLM →
    parses structured output → returns typed Extractions.
    """

    def __init__(self, profile: ExtractionProfile):
        self.profile = profile
        self.model = profile.llm.model or settings.LLM_MODEL
        self.temperature = profile.llm.temperature
        self.max_tokens = profile.llm.max_tokens
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._last_tokens = 0

    async def extract(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Run extraction pipeline: build prompt → call LLM → parse → filter."""
        start_ms = int(time.time() * 1000)

        prompt = build_extraction_prompt(self.profile, transcript, participants)

        try:
            raw_json = await self._call_llm(prompt)
        except Exception as e:
            logger.error("LLM extraction failed: %s", e)
            raise

        extractions = self._parse_extractions(raw_json)
        # Store all extractions regardless of confidence — low-confidence items
        # are valuable for calibration. Clients can filter by threshold if needed.

        summary = raw_json.get("summary", "")
        duration_ms = int(time.time() * 1000) - start_ms

        logger.info(
            "Extraction complete: profile=%s extractions=%d tokens=%d ms=%d",
            self.profile.profile_id,
            len(extractions),
            self._last_tokens,
            duration_ms,
        )

        return ExtractionResult(
            extractions=extractions,
            summary=summary,
            model_used=self.model,
            tokens_used=self._last_tokens,
            duration_ms=duration_ms,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_llm(self, prompt: str) -> dict:
        """Call OpenAI with retry logic. Returns parsed JSON dict."""
        create_kwargs = dict(
            model=self.model,
            max_completion_tokens=self.max_tokens,
        )
        # Some models (e.g., gpt-5-mini) only support temperature=1
        if "gpt-5" not in self.model:
            create_kwargs["temperature"] = self.temperature

        response = await self._client.chat.completions.create(
            **create_kwargs,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        self._last_tokens = response.usage.total_tokens if response.usage else 0
        content = response.choices[0].message.content or "{}"

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON: %s\nContent: %s", e, content[:500])
            raise ValueError(f"LLM returned invalid JSON: {e}") from e

    def _parse_extractions(self, raw: dict) -> list[ExtractedItem]:
        """Parse raw LLM response into ExtractedItem objects."""
        logger.debug("Raw LLM response keys: %s, extraction count: %d",
                      list(raw.keys()), len(raw.get("extractions", [])))
        items = []
        for item in raw.get("extractions", []):
            if item is None:
                continue
            try:
                items.append(
                    ExtractedItem(
                        extraction_type=str(item.get("extraction_type", "UNKNOWN")).upper(),
                        description=str(item.get("description", "")),
                        confidence=float(item.get("confidence", 0.0)),
                        attributed_to=item.get("attributed_to"),
                        evidence=item.get("evidence"),
                        attributes=item.get("attributes", {}),
                    )
                )
            except (TypeError, ValueError) as e:
                logger.warning("Skipping malformed extraction item: %s — %s", item, e)
        return items
