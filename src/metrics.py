"""Compute ops metrics and export to CSV for Tableau.

Metrics map directly to the JD: efficiency gains, insight reuse,
adoption, and the AI override rate.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

import pandas as pd

from . import config, repository

# Assumption stated openly in the demo: manual minutes to tag one transcript.
MANUAL_MINUTES_PER_TRANSCRIPT = 45


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def time_to_insight() -> dict:
    """Average time (minutes) from study creation to its first approved insight."""
    studies = {s["id"]: s for s in repository.list_studies()}
    insights = repository.list_insights()

    first_insight: dict[str, datetime] = {}
    for ins in insights:
        sid = ins.get("study_id")
        created = _parse(ins.get("created_at"))
        if sid and created and (sid not in first_insight or created < first_insight[sid]):
            first_insight[sid] = created

    deltas = []
    for sid, first_ts in first_insight.items():
        study = studies.get(sid)
        if not study:
            continue
        start = _parse(study.get("created_at"))
        if start:
            deltas.append((first_ts - start).total_seconds() / 60.0)

    avg = round(sum(deltas) / len(deltas), 1) if deltas else 0.0
    return {"avg_minutes": avg, "studies_measured": len(deltas)}


def override_rate() -> dict:
    """Share of AI suggestions approved as-is vs edited vs rejected."""
    actions = Counter(row["action"] for row in repository.list_audit_log())
    total = sum(actions.values())
    if total == 0:
        return {"total": 0, "approve": 0, "edit": 0, "reject": 0,
                "approve_pct": 0.0, "edit_pct": 0.0, "reject_pct": 0.0}
    return {
        "total": total,
        "approve": actions.get("approve", 0),
        "edit": actions.get("edit", 0),
        "reject": actions.get("reject", 0),
        "approve_pct": round(100 * actions.get("approve", 0) / total, 1),
        "edit_pct": round(100 * actions.get("edit", 0) / total, 1),
        "reject_pct": round(100 * actions.get("reject", 0) / total, 1),
    }


def insight_reuse() -> dict:
    """How often stored insights are surfaced by searches."""
    searches = repository.list_search_log()
    counts: Counter = Counter()
    for s in searches:
        try:
            import json
            for iid in json.loads(s.get("returned_insight_ids") or "[]"):
                counts[iid] += 1
        except (ValueError, TypeError):
            continue
    return {"total_searches": len(searches), "total_retrievals": sum(counts.values())}


def adoption() -> dict:
    return {
        "studies": len(repository.list_studies()),
        "insights": len(repository.list_insights()),
    }


def hours_saved() -> dict:
    """Estimated manual hours saved, given the stated assumption."""
    n_insights = len(repository.list_insights())
    studies = repository.list_studies()
    saved_minutes = len(studies) * MANUAL_MINUTES_PER_TRANSCRIPT
    return {
        "assumption_min_per_transcript": MANUAL_MINUTES_PER_TRANSCRIPT,
        "estimated_hours_saved": round(saved_minutes / 60.0, 1),
        "insights_generated": n_insights,
    }


def export_csv() -> str:
    """Write a flat metrics snapshot to outputs/metrics_export.csv."""
    snapshot = {
        **{f"ttv_{k}": v for k, v in time_to_insight().items()},
        **{f"override_{k}": v for k, v in override_rate().items()},
        **{f"reuse_{k}": v for k, v in insight_reuse().items()},
        **{f"adoption_{k}": v for k, v in adoption().items()},
        **{f"saved_{k}": v for k, v in hours_saved().items()},
    }
    df = pd.DataFrame([snapshot])
    df.to_csv(config.METRICS_CSV_PATH, index=False)
    return str(config.METRICS_CSV_PATH)
