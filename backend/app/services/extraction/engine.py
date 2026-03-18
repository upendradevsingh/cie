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
from app.services.extraction.behavioral_prompts import (
    BEHAVIORAL_SYSTEM_PROMPT,
    BEHAVIORAL_TYPES,
    CONTENT_TYPES,
)
from app.services.extraction.prompts import (
    SYSTEM_PROMPT,
    build_extraction_prompt,
    build_extraction_prompt_for_types,
)
from app.services.extraction.transcript_cleanup import (
    CLEANUP_SYSTEM_PROMPT,
    build_cleanup_prompt,
)

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

    def __init__(
        self,
        profile: ExtractionProfile,
        extraction_mode: str = "single_pass",
    ):
        self.profile = profile
        self.extraction_mode = extraction_mode
        self.model = profile.llm.model or settings.LLM_MODEL
        self.temperature = profile.llm.temperature
        self.max_tokens = profile.llm.max_tokens
        # Create client lazily per call — AsyncOpenAI binds to event loop on first use
        self._api_key = settings.OPENAI_API_KEY
        self._last_tokens = 0

    async def extract(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Run extraction pipeline: cleanup → build prompt → call LLM → parse."""
        # Pass 0: Clean up messy auto-transcribed text
        clean_transcript = await self._cleanup_transcript(transcript, participants)

        if self.extraction_mode == "two_pass":
            return await self._extract_two_pass(clean_transcript, participants)
        return await self._extract_single_pass(clean_transcript, participants)

    async def _cleanup_transcript(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
    ) -> str:
        """Pass 0: Clean up auto-transcribed text before extraction."""
        # Skip cleanup for short/clean transcripts
        if len(transcript) < 100:
            return transcript

        cleanup_prompt = build_cleanup_prompt(transcript, participants)

        try:
            client = openai.AsyncOpenAI(api_key=self._api_key)
            response = await client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": CLEANUP_SYSTEM_PROMPT},
                    {"role": "user", "content": cleanup_prompt},
                ],
            )
            clean = response.choices[0].message.content or transcript
            cleanup_tokens = response.usage.total_tokens if response.usage else 0
            self._last_tokens += cleanup_tokens
            logger.info(
                "Transcript cleanup: %d→%d chars, %d tokens",
                len(transcript), len(clean), cleanup_tokens,
            )
            return clean
        except Exception as e:
            logger.warning("Transcript cleanup failed, using raw: %s", e)
            return transcript

    async def _extract_single_pass(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Single-pass extraction: one LLM call with all types."""
        start_ms = int(time.time() * 1000)

        prompt = build_extraction_prompt(self.profile, transcript, participants)

        try:
            raw_json = await self._call_llm(prompt)
        except Exception as e:
            logger.error("LLM extraction failed: %s", e)
            raise

        extractions = self._parse_extractions(raw_json)
        summary = raw_json.get("summary", "")
        duration_ms = int(time.time() * 1000) - start_ms

        logger.info(
            "Extraction complete (single_pass): profile=%s extractions=%d tokens=%d ms=%d",
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

    async def _extract_two_pass(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Two-pass extraction: content pass + behavioral pass, merged."""
        start_ms = int(time.time() * 1000)
        total_tokens = 0

        # Pass 1 — Content extraction (what was said)
        content_prompt = build_extraction_prompt_for_types(
            self.profile, transcript, participants, type_filter=CONTENT_TYPES,
        )
        try:
            content_raw = await self._call_llm(content_prompt)
        except Exception as e:
            logger.error("Content pass LLM extraction failed: %s", e)
            raise
        content_extractions = self._parse_extractions(content_raw)
        total_tokens += self._last_tokens
        summary = content_raw.get("summary", "")

        # Pass 2 — Behavioral extraction (how it was said)
        behavioral_prompt = build_extraction_prompt_for_types(
            self.profile, transcript, participants, type_filter=BEHAVIORAL_TYPES,
        )
        try:
            behavioral_raw = await self._call_llm(
                behavioral_prompt, system_prompt=BEHAVIORAL_SYSTEM_PROMPT,
            )
        except Exception as e:
            logger.error("Behavioral pass LLM extraction failed: %s", e)
            raise
        behavioral_extractions = self._parse_extractions(behavioral_raw)
        total_tokens += self._last_tokens

        # Merge both passes
        all_extractions = content_extractions + behavioral_extractions
        self._last_tokens = total_tokens
        duration_ms = int(time.time() * 1000) - start_ms

        logger.info(
            "Extraction complete (two_pass): profile=%s content=%d behavioral=%d total=%d tokens=%d ms=%d",
            self.profile.profile_id,
            len(content_extractions),
            len(behavioral_extractions),
            len(all_extractions),
            total_tokens,
            duration_ms,
        )

        return ExtractionResult(
            extractions=all_extractions,
            summary=summary,
            model_used=self.model,
            tokens_used=total_tokens,
            duration_ms=duration_ms,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_llm(
        self, prompt: str, system_prompt: str | None = None,
    ) -> dict:
        """Call OpenAI with retry logic. Returns parsed JSON dict."""
        create_kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        sys_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT

        # Fresh client per call to avoid stale event loop binding in Celery workers
        client = openai.AsyncOpenAI(api_key=self._api_key)
        response = await client.chat.completions.create(
            **create_kwargs,
            messages=[
                {"role": "system", "content": sys_prompt},
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
