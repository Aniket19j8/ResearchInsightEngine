"""Transcript -> AI-suggested themes/quotes/insights.

Two anti-hallucination guardrails:
  1. themes are constrained to the controlled taxonomy
  2. quotes must be copied verbatim from the transcript

If the LLM is unavailable, a deterministic keyword tagger produces
suggestions so the workflow still works offline.
"""
from __future__ import annotations

import json
import re

from . import config, llm, privacy

PROMPT_TEMPLATE = """You are assisting a UX researcher. From the interview transcript, extract findings.

Return JSON only, as an object with a single key "items" whose value is a list of objects.
Each object MUST have these keys: theme, quote, draft_insight, severity, confidence.

Rules:
- "theme" MUST be exactly one of: {allowed_themes}
- "severity" MUST be exactly one of: {allowed_severities}
- "quote" MUST be copied verbatim from the transcript (no paraphrasing).
- "draft_insight" is one concise sentence describing the finding.
- "confidence" is your certainty from 0 to 1.

Transcript:
\"\"\"
{transcript}
\"\"\"
"""

# Lightweight keyword cues for the offline fallback tagger.
_KEYWORD_CUES = {
    "onboarding": ["sign up", "sign-up", "first time", "welcome", "get started", "start here", "tour"],
    "navigation": ["menu", "navigate", "find", "label", "click", "tab"],
    "accessibility": ["caption", "screen reader", "contrast", "accessib"],
    "content_quality": ["content", "lesson", "material", "video quality", "module"],
    "pacing": ["pace", "pacing", "workload", "too fast", "too slow", "time"],
    "mobile_experience": ["mobile", "phone", "screen", "scroll", "app"],
    "performance": ["slow", "load", "timed out", "timeout", "lag", "crash"],
    "positive": ["love", "great", "like", "good", "genuinely"],
    "feature_request": ["wish", "would be nice", "should add", "feature", "request", "would have helped"],
}


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _fallback_synthesis(transcript: str) -> list[dict]:
    """Deterministic keyword tagger used when the LLM is unavailable."""
    themes = config.allowed_themes()
    items: list[dict] = []
    seen_themes: set[str] = set()
    for sentence in _split_sentences(transcript):
        lower = sentence.lower()
        for theme in themes:
            if theme in seen_themes:
                continue
            cues = _KEYWORD_CUES.get(theme, [theme])
            if any(cue in lower for cue in cues):
                items.append({
                    "theme": theme,
                    "quote": sentence,
                    "draft_insight": f"Learner comment related to {theme.replace('_', ' ')}.",
                    "severity": "medium",
                    "confidence": 0.4,
                })
                seen_themes.add(theme)
                break
    return items


def _validate(items: list[dict], transcript: str) -> list[dict]:
    """Keep only suggestions that respect the guardrails."""
    themes = set(config.allowed_themes())
    severities = set(config.allowed_severities())
    normalized = transcript.lower()
    clean: list[dict] = []
    for it in items:
        theme = str(it.get("theme", "")).strip()
        quote = str(it.get("quote", "")).strip()
        if theme not in themes or not quote:
            continue
        # Enforce verbatim-quote guardrail (loose: substring match).
        if quote.lower() not in normalized:
            continue
        severity = it.get("severity", "medium")
        if severity not in severities:
            severity = "medium"
        try:
            confidence = float(it.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        clean.append({
            "theme": theme,
            "quote": quote,
            "draft_insight": str(it.get("draft_insight", "")).strip() or quote,
            "severity": severity,
            "confidence": max(0.0, min(1.0, confidence)),
        })
    return clean


def synthesize(transcript: str) -> dict:
    """Return {'items': [...], 'source': 'llm'|'fallback', 'pii_report': {...}}.

    PII is scrubbed BEFORE the text reaches the LLM (red-lane governance).
    All downstream validation and quoting uses the scrubbed text, so no raw
    participant identifiers are ever stored or sent externally.
    """
    clean_transcript, pii_report = privacy.scrub_pii(transcript)

    prompt = PROMPT_TEMPLATE.format(
        allowed_themes=", ".join(config.allowed_themes()),
        allowed_severities=", ".join(config.allowed_severities()),
        transcript=clean_transcript,
    )
    raw = llm.complete(prompt, json_mode=True)
    if raw:
        try:
            data = json.loads(raw)
            items = data.get("items", []) if isinstance(data, dict) else data
            validated = _validate(items, clean_transcript)
            if validated:
                return {"items": validated, "source": "llm", "pii_report": pii_report}
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "items": _fallback_synthesis(clean_transcript),
        "source": "fallback",
        "pii_report": pii_report,
    }


def summarize_document(text: str) -> dict:
    """Summarize an uploaded document or research paper.

    Returns {'summary': str, 'key_points': [str], 'source': 'llm'|'fallback',
    'pii_report': {...}}. PII is scrubbed before the LLM sees the text.
    """
    clean_text, pii_report = privacy.scrub_pii(text)
    truncated = clean_text[:12000]  # keep the prompt within a safe size

    prompt = (
        "You are assisting a UX researcher. Summarize the following document.\n"
        'Return JSON only, an object with keys "summary" (3-5 sentences) and '
        '"key_points" (a list of 3-7 short bullet strings) and '
        '"techniques" (a list of any methods/techniques mentioned, may be empty).\n\n'
        f"Document:\n\"\"\"\n{truncated}\n\"\"\""
    )
    raw = llm.complete(prompt, json_mode=True)
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("summary"):
                return {
                    "summary": str(data.get("summary", "")).strip(),
                    "key_points": [str(p) for p in data.get("key_points", [])],
                    "techniques": [str(t) for t in data.get("techniques", [])],
                    "source": "llm",
                    "pii_report": pii_report,
                }
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: naive extractive summary (first few substantial sentences).
    sentences = _split_sentences(clean_text)
    return {
        "summary": " ".join(sentences[:3]) if sentences else "(No text extracted.)",
        "key_points": sentences[3:8],
        "techniques": [],
        "source": "fallback",
        "pii_report": pii_report,
    }


def generate_study_report(study: dict, insights: list[dict]) -> dict:
    """Build an executive summary for a study from its approved insights.

    Returns {'summary': str, 'source': 'llm'|'fallback'}.
    """
    if not insights:
        return {"summary": "No approved insights yet for this study.", "source": "fallback"}

    bullet_lines = "\n".join(
        f"- [{i.get('theme')} / {i.get('severity')}] {i.get('insight')}"
        for i in insights
    )

    prompt = (
        "You are a UX research lead writing an executive summary for stakeholders.\n"
        f"Study: {study.get('title')}\n"
        f"Research question: {study.get('research_question', 'N/A')}\n\n"
        "Approved insights:\n"
        f"{bullet_lines}\n\n"
        "Write a concise executive summary (4-6 sentences) that synthesizes the "
        "top themes, highlights the most severe issues, and notes any positive "
        "findings. Plain prose, no markdown headers."
    )
    raw = llm.complete(prompt)
    if raw and raw.strip():
        return {"summary": raw.strip(), "source": "llm"}

    # Fallback: deterministic template grouped by theme.
    from collections import Counter

    theme_counts = Counter(i.get("theme") for i in insights)
    high = [i for i in insights if i.get("severity") == "high"]
    lines = [
        f"This study captured {len(insights)} approved insights across "
        f"{len(theme_counts)} themes.",
        "Most common themes: "
        + ", ".join(f"{t} ({c})" for t, c in theme_counts.most_common(3)) + ".",
    ]
    if high:
        lines.append(f"{len(high)} high-severity issue(s) require attention.")
    return {"summary": " ".join(lines), "source": "fallback"}
