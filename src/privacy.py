"""PII scrubbing — pseudonymize participant identifiers before any text
reaches an external LLM (the red-lane requirement in the governance policy).

This is a lightweight, dependency-free regex scrubber. It covers the most
common identifiers (emails, phones, SSNs, credit cards, URLs, and simple
"my name is X" patterns). For production, swap in Microsoft Presidio or a
spaCy NER model for far better name/location coverage — the call site
stays the same.
"""
from __future__ import annotations

import re

# Order matters: more specific patterns first so they win over general ones.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("PHONE", re.compile(
        r"\b(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b"
    )),
    ("URL", re.compile(r"\bhttps?://[^\s]+\b")),
    # "My name is John", "I'm Jane", "I am Bob Smith"
    ("NAME", re.compile(
        r"\b(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        re.IGNORECASE,
    )),
]


def scrub_pii(text: str) -> tuple[str, dict]:
    """Replace detected PII with placeholder tokens.

    Returns (clean_text, report) where report maps each PII type to the
    number of redactions made. The report is shown to the researcher so
    redaction is transparent and auditable.
    """
    if not text:
        return text, {}

    report: dict[str, int] = {}
    clean = text

    for label, pattern in _PATTERNS:
        if label == "NAME":
            # Only redact the captured name group, keep the lead-in phrase.
            def _name_sub(match: re.Match) -> str:
                report[label] = report.get(label, 0) + 1
                return match.group(0).replace(match.group(1), f"[{label}]")

            clean = pattern.sub(_name_sub, clean)
            continue

        def _sub(match: re.Match, _label: str = label) -> str:
            report[_label] = report.get(_label, 0) + 1
            return f"[{_label}]"

        clean = pattern.sub(_sub, clean)

    return clean, report


def has_pii(text: str) -> bool:
    """Quick check whether any PII pattern matches."""
    _, report = scrub_pii(text)
    return bool(report)


def summarize_report(report: dict) -> str:
    """Human-readable one-line summary of a redaction report."""
    if not report:
        return "No PII detected."
    parts = [f"{count} {label.lower().replace('_', ' ')}" for label, count in report.items()]
    return "Redacted: " + ", ".join(parts) + "."
