"""Tier 3: Multi-model consensus annotation.

Sends same transcript to gpt-4o, claude-sonnet, gemini-pro.
Computes consensus via extraction type matching.
Outputs gold dataset entry with agreement metadata.

Usage:
    python -m tests.eval.annotation.multi_model --input transcript.txt

Requires: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
"""
import argparse
import json
import os
import sys
from datetime import date
from typing import Optional

# Import extraction prompt builder
from app.profiles import ProfileLoader
from app.services.extraction.prompts import SYSTEM_PROMPT, build_extraction_prompt


def _call_openai(system: str, prompt: str) -> list[dict]:
    """Call OpenAI gpt-4o and return extractions."""
    import openai
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    resp = client.chat.completions.create(
        model="gpt-4o", temperature=0.15, max_tokens=4096,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    return data.get("extractions", [])


def _call_anthropic(system: str, prompt: str) -> list[dict]:
    """Call Anthropic Claude and return extractions."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ANTHROPIC_API_KEY not set — skipping Claude", file=sys.stderr)
        return []
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=4096, temperature=0.15,
            system=system,
            messages=[{"role": "user", "content": prompt + "\n\nReturn ONLY valid JSON."}],
        )
        text = resp.content[0].text
        # Try to parse JSON from response
        data = json.loads(text)
        return data.get("extractions", [])
    except Exception as e:
        print(f"  Claude error: {e}", file=sys.stderr)
        return []


def _call_gemini(system: str, prompt: str) -> list[dict]:
    """Call Google Gemini and return extractions."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("  GOOGLE_API_KEY not set — skipping Gemini", file=sys.stderr)
        return []
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        full_prompt = f"{system}\n\n{prompt}\n\nReturn ONLY valid JSON."
        resp = model.generate_content(full_prompt)
        text = resp.text
        # Clean markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())
        return data.get("extractions", [])
    except Exception as e:
        print(f"  Gemini error: {e}", file=sys.stderr)
        return []


def compute_consensus(model_results: dict[str, list[dict]]) -> dict:
    """Compare extractions across models and compute consensus.

    Agreement rules:
    - 3/3 models agree on extraction type -> auto-accept
    - 2/3 agree -> accept with flag
    - 1/3 only -> human adjudication
    - 0/3 -> discard
    """
    # Group all extractions by type
    type_extractions: dict[str, list[tuple[str, dict]]] = {}
    for model_name, extractions in model_results.items():
        for ext in extractions:
            ext_type = ext.get("extraction_type", "UNKNOWN").upper()
            if ext_type not in type_extractions:
                type_extractions[ext_type] = []
            type_extractions[ext_type].append((model_name, ext))

    consensus_items = []
    adjudication_needed = []

    for ext_type, model_exts in type_extractions.items():
        models_with_type = set(m for m, _ in model_exts)
        agreement = len(models_with_type)

        # Pick the best description (longest, most detailed)
        best_ext = max(model_exts, key=lambda x: len(x[1].get("description", "")))[1]

        # Extract keywords from description
        desc = best_ext.get("description", "")
        words = desc.split()
        stop_words = {"the", "and", "for", "that", "this", "with", "from", "will", "was", "are", "not", "has", "had"}
        keywords = [w.strip(".,;:!?\"'") for w in words if len(w) > 3 and w.lower() not in stop_words][:5]

        item = {
            "extraction_type": ext_type,
            "description_contains": keywords,
            "min_confidence": 0.60,
            "agreement": f"{agreement}/3",
            "models_agreeing": sorted(models_with_type),
        }

        if agreement >= 2:
            consensus_items.append(item)
        else:
            item["needs_adjudication"] = True
            item["model_descriptions"] = {m: e.get("description", "") for m, e in model_exts}
            adjudication_needed.append(item)

    return {
        "consensus": consensus_items,
        "adjudication": adjudication_needed,
        "agreement_rate": len(consensus_items) / max(1, len(consensus_items) + len(adjudication_needed)),
    }


def generate_consensus_entry(
    transcript_text: str,
    profile_id: str = "performance",
    entry_id: Optional[str] = None,
    title: str = "Untitled",
) -> dict:
    """Run multi-model extraction and build consensus gold entry."""
    loader = ProfileLoader()
    profile = loader.load(profile_id)
    prompt = build_extraction_prompt(profile, transcript_text, [])

    print("Running extractions across models...", file=sys.stderr)

    model_results = {}

    print("  -> gpt-4o...", file=sys.stderr)
    model_results["gpt-4o"] = _call_openai(SYSTEM_PROMPT, prompt)
    print(f"    {len(model_results['gpt-4o'])} extractions", file=sys.stderr)

    print("  -> claude...", file=sys.stderr)
    model_results["claude"] = _call_anthropic(SYSTEM_PROMPT, prompt)
    print(f"    {len(model_results['claude'])} extractions", file=sys.stderr)

    print("  -> gemini...", file=sys.stderr)
    model_results["gemini"] = _call_gemini(SYSTEM_PROMPT, prompt)
    print(f"    {len(model_results['gemini'])} extractions", file=sys.stderr)

    # Compute consensus
    consensus = compute_consensus(model_results)

    active_models = [m for m, exts in model_results.items() if exts]

    entry = {
        "id": entry_id or f"gold_consensus_{date.today().isoformat()}",
        "name": title,
        "category": "real_transcript",
        "profile": profile_id,
        "annotation_method": "multi_model_consensus",
        "annotated_by": "consensus",
        "annotation_date": date.today().isoformat(),
        "consensus_models": active_models,
        "agreement_rate": round(consensus["agreement_rate"], 2),
        "adjudicated_items": consensus["adjudication"],
        "participants": [],
        "segments": [{"speaker": "Transcript", "text": transcript_text, "startTime": 0, "endTime": 0}],
        "expected_extractions": consensus["consensus"],
        "expected_absent": [],
        "tags": ["real", "multi_model_consensus"],
    }

    return entry


def main():
    parser = argparse.ArgumentParser(description="Multi-model consensus annotation")
    parser.add_argument("--input", "-i", help="Transcript file")
    parser.add_argument("--profile", "-p", default="performance")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--id", help="Gold entry ID")
    parser.add_argument("--title", "-t", default="Untitled")
    args = parser.parse_args()

    if args.input and args.input != "-":
        with open(args.input) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("Error: empty transcript", file=sys.stderr)
        sys.exit(1)

    entry = generate_consensus_entry(text, args.profile, args.id, args.title)

    output = json.dumps(entry, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\nConsensus entry written to {args.output}", file=sys.stderr)
    else:
        print(output)

    # Summary
    print(f"\nModels used: {len(entry['consensus_models'])}", file=sys.stderr)
    print(f"Agreement rate: {entry['agreement_rate']:.0%}", file=sys.stderr)
    print(f"Consensus items: {len(entry['expected_extractions'])}", file=sys.stderr)
    print(f"Needs adjudication: {len(entry['adjudicated_items'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
