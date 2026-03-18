"""Tier 2: LLM-Assist annotation for real transcripts.

Takes a real transcript, runs it through CIE's ExtractionEngine, and outputs
a draft gold dataset entry (JSON) for human review before inclusion in
gold_dataset.json.

Usage:
    python -m tests.eval.annotation.llm_assist --input transcript.txt
    python -m tests.eval.annotation.llm_assist --input transcript.txt --profile performance --output draft.json
    echo "Manager: How's the project?" | python -m tests.eval.annotation.llm_assist
"""
import argparse
import asyncio
import json
import sys
from datetime import date

from app.profiles import ProfileLoader
from app.services.extraction.engine import ExtractionEngine


STOP_WORDS = frozenset({
    "the", "and", "for", "that", "this", "with", "from", "will", "was",
    "has", "had", "are", "not", "but", "can", "all", "been", "have",
    "were", "they", "their", "there", "would", "could", "should", "about",
    "into", "more", "some", "than", "them", "then", "what", "when",
})


def _extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """Pull significant words from text for fuzzy matching."""
    words = text.split()
    keywords = [
        w.strip(".,;:!?\"'()[]")
        for w in words
        if len(w) > 3 and w.lower() not in STOP_WORDS
    ]
    return keywords[:max_keywords]


def generate_gold_entry(
    transcript_text: str,
    profile_id: str = "performance",
    entry_id: str | None = None,
    title: str = "Untitled Conversation",
) -> dict:
    """Run CIE extraction and produce a draft gold dataset entry.

    Uses asyncio.new_event_loop() instead of asyncio.run() for Celery
    compatibility — avoids conflicts with already-running loops.
    """
    loader = ProfileLoader()
    profile = loader.load(profile_id)
    engine = ExtractionEngine(profile)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(engine.extract(transcript_text, []))
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    # Convert extractions to expected_extractions format
    expected: list[dict] = []
    for ext in result.extractions:
        keywords = _extract_keywords(ext.description)
        expected.append({
            "extraction_type": ext.extraction_type,
            "description_contains": keywords,
            "min_confidence": round(max(0.5, ext.confidence - 0.15), 2),
        })

    entry = {
        "id": entry_id or f"gold_real_{date.today().isoformat()}",
        "name": title,
        "category": "real_transcript",
        "profile": profile_id,
        "annotation_method": "llm_assist",
        "annotated_by": "pending_review",
        "annotation_date": date.today().isoformat(),
        "participants": [],
        "segments": [
            {
                "speaker": "Transcript",
                "text": transcript_text,
                "startTime": 0,
                "endTime": 0,
            },
        ],
        "expected_extractions": expected,
        "expected_absent": [],
        "tags": ["real", "llm_assist", "pending_review"],
    }

    return entry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate draft gold dataset entry from transcript",
    )
    parser.add_argument(
        "--input", "-i",
        help="Transcript text file (use - or omit for stdin)",
    )
    parser.add_argument(
        "--profile", "-p",
        default="performance",
        help="CIE profile to use (default: performance)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file (default: stdout)",
    )
    parser.add_argument(
        "--id",
        help="Gold entry ID (default: gold_real_<date>)",
    )
    parser.add_argument(
        "--title", "-t",
        default="Untitled Conversation",
        help="Conversation title",
    )
    args = parser.parse_args()

    # Read transcript
    if args.input and args.input != "-":
        with open(args.input) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("Error: empty transcript", file=sys.stderr)
        sys.exit(1)

    # Generate draft entry
    entry = generate_gold_entry(text, args.profile, args.id, args.title)

    # Output
    output = json.dumps(entry, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")
        print(f"Draft gold entry written to {args.output}", file=sys.stderr)
        print(f"  Extractions: {len(entry['expected_extractions'])}", file=sys.stderr)
        print("  Review and edit before adding to gold_dataset.json", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
