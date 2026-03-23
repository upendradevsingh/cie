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
        self._parallel_tokens: dict[str, int] = {}  # per-label token tracking for parallel calls

    async def extract(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
        segments: list[dict[str, Any]] | None = None,
        meeting_type: str | None = None,
        db=None,
        tenant_id=None,
    ) -> ExtractionResult:
        """Run extraction pipeline: cleanup → build prompt → call LLM → parse."""
        self._meeting_type = meeting_type
        self._db = db
        self._tenant_id = tenant_id

        # Build speaker-tagged transcript from segments if available
        # This preserves ASR speaker attribution through the cleanup pass
        if segments:
            tagged_transcript = self._build_speaker_tagged_transcript(segments)
        else:
            tagged_transcript = transcript

        # Pass 0: Clean up messy auto-transcribed text
        clean_transcript = await self._cleanup_transcript(tagged_transcript, participants)

        if self.extraction_mode == "two_pass":
            return await self._extract_two_pass(clean_transcript, participants)
        return await self._extract_single_pass(clean_transcript, participants)

    @staticmethod
    def _build_speaker_tagged_transcript(segments: list[dict[str, Any]]) -> str:
        """Build a speaker-tagged transcript from segments.

        Merges consecutive segments from the same speaker into one line.
        Output format: "Speaker Name: text\nOther Speaker: text\n..."
        """
        lines: list[str] = []
        current_speaker: str | None = None
        current_texts: list[str] = []

        for seg in segments:
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "").strip()
            if not text:
                continue

            if speaker == current_speaker:
                current_texts.append(text)
            else:
                if current_speaker and current_texts:
                    lines.append(f"{current_speaker}: {' '.join(current_texts)}")
                current_speaker = speaker
                current_texts = [text]

        # Flush last speaker
        if current_speaker and current_texts:
            lines.append(f"{current_speaker}: {' '.join(current_texts)}")

        return "\n".join(lines)

    async def _cleanup_transcript(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
    ) -> str:
        """Pass 0: Clean up auto-transcribed text before extraction."""
        # Skip cleanup for short/clean transcripts
        if len(transcript) < 100:
            return transcript

        cleanup_prompt = build_cleanup_prompt(
            transcript, participants, meeting_type=self._meeting_type,
        )

        try:
            cleanup_start = time.time()
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
            cleanup_ms = int((time.time() - cleanup_start) * 1000)
            clean = response.choices[0].message.content or transcript
            cleanup_tokens = response.usage.total_tokens if response.usage else 0
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            self._last_tokens += cleanup_tokens
            logger.info(
                "OpenAI pass0_cleanup: model=%s latency=%dms tokens(in=%d out=%d total=%d) chars(%d→%d)",
                self.model, cleanup_ms, input_tokens, output_tokens,
                cleanup_tokens, len(transcript), len(clean),
            )
            return clean
        except Exception as e:
            logger.warning("Transcript cleanup failed, using raw: %s", e)
            return transcript

    def _get_correction_examples(self, extraction_types: set[str]) -> dict[str, str]:
        """Query correction feedback if DB session is available."""
        if not self._db or not self._tenant_id:
            return {}
        try:
            from app.services.extraction.correction_feedback import get_correction_examples
            return get_correction_examples(
                self._db, self._tenant_id, self.profile.profile_id, extraction_types,
            )
        except Exception as e:
            logger.warning("Failed to load correction feedback: %s", e)
            return {}

    async def _extract_single_pass(
        self,
        transcript: str,
        participants: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Single-pass extraction: one LLM call with all types."""
        start_ms = int(time.time() * 1000)

        all_types = set(self.profile.enabled_types().keys())
        corrections = self._get_correction_examples(all_types)

        prompt = build_extraction_prompt(
            self.profile, transcript, participants, meeting_type=self._meeting_type,
            correction_examples=corrections,
        )

        try:
            raw_json = await self._call_llm(prompt, label="single_pass")
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
        """Two-pass extraction: content + behavioral in PARALLEL, then merged."""
        import asyncio
        start_ms = int(time.time() * 1000)

        # Query correction feedback for both passes
        content_corrections = self._get_correction_examples(CONTENT_TYPES)
        behavioral_corrections = self._get_correction_examples(BEHAVIORAL_TYPES)

        # Build both prompts
        content_prompt = build_extraction_prompt_for_types(
            self.profile, transcript, participants, type_filter=CONTENT_TYPES,
            meeting_type=self._meeting_type, correction_examples=content_corrections,
        )
        behavioral_prompt = build_extraction_prompt_for_types(
            self.profile, transcript, participants, type_filter=BEHAVIORAL_TYPES,
            meeting_type=self._meeting_type, correction_examples=behavioral_corrections,
        )

        # Run Pass 1 and Pass 2 in parallel — they're independent
        content_task = self._call_llm(content_prompt, label="pass1_content")
        behavioral_task = self._call_llm(
            behavioral_prompt, system_prompt=BEHAVIORAL_SYSTEM_PROMPT,
            label="pass2_behavioral",
        )

        try:
            content_raw, behavioral_raw = await asyncio.gather(
                content_task, behavioral_task,
            )
        except Exception as e:
            logger.error("Parallel extraction failed: %s", e)
            raise

        content_extractions = self._parse_extractions(content_raw)
        behavioral_extractions = self._parse_extractions(behavioral_raw)
        summary = content_raw.get("summary", "")

        # Merge both passes — token count from _last_tokens is unreliable
        # in parallel, so sum from response usage tracked per-call
        all_extractions = content_extractions + behavioral_extractions
        total_tokens = self._parallel_tokens.get("pass1_content", 0) + \
                       self._parallel_tokens.get("pass2_behavioral", 0)
        self._last_tokens = total_tokens
        duration_ms = int(time.time() * 1000) - start_ms

        logger.info(
            "Extraction complete (two_pass_parallel): profile=%s content=%d behavioral=%d total=%d tokens=%d ms=%d",
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
        label: str = "llm_call",
    ) -> dict:
        """Call OpenAI with retry logic. Returns parsed JSON dict."""
        call_start = time.time()
        create_kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        sys_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT
        prompt_tokens = len(prompt.split()) + len(sys_prompt.split())  # rough estimate

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

        call_ms = int((time.time() - call_start) * 1000)
        self._last_tokens = response.usage.total_tokens if response.usage else 0
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        content = response.choices[0].message.content or "{}"

        self._parallel_tokens[label] = self._last_tokens
        logger.info(
            "OpenAI %s: model=%s latency=%dms tokens(in=%d out=%d total=%d) prompt_words≈%d",
            label, self.model, call_ms, input_tokens, output_tokens,
            self._last_tokens, prompt_tokens,
        )
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
