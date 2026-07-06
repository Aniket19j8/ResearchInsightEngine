"""SQLite persistence: studies, insights, audit log.

A single file database (no server). This is the system of record for
approved insights and the full audit trail of human decisions.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Create tables if they do not already exist. Safe to call repeatedly."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS studies (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                research_question TEXT,
                method TEXT,
                product_area TEXT,
                persona TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                study_id TEXT,
                theme TEXT NOT NULL,
                quote TEXT NOT NULL,
                insight TEXT NOT NULL,
                severity TEXT,
                confidence REAL,
                source TEXT,            -- 'ai_approved' or 'human_edited'
                created_at TEXT NOT NULL,
                FOREIGN KEY (study_id) REFERENCES studies(id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_id TEXT,
                study_id TEXT,
                action TEXT NOT NULL,   -- 'approve' | 'edit' | 'reject'
                ai_value TEXT,          -- JSON of the AI's original suggestion
                human_value TEXT,       -- JSON of the human's final decision
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS search_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                returned_insight_ids TEXT,  -- JSON list
                timestamp TEXT NOT NULL
            );
            """
        )


# --- Studies ---------------------------------------------------------------
def create_study(study_id: str, title: str, research_question: str,
                 method: str, product_area: str, persona: str) -> dict:
    created_at = _now()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO studies
               (id, title, research_question, method, product_area, persona, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (study_id, title, research_question, method, product_area, persona, created_at),
        )
    return {"id": study_id, "title": title, "created_at": created_at}


def list_studies() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM studies ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# --- Insights --------------------------------------------------------------
def save_insight(insight_id: str, study_id: str, theme: str, quote: str,
                 insight: str, severity: str, confidence: float, source: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO insights
               (id, study_id, theme, quote, insight, severity, confidence, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (insight_id, study_id, theme, quote, insight, severity,
             confidence, source, _now()),
        )


def list_insights(study_id: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if study_id:
            rows = conn.execute(
                "SELECT * FROM insights WHERE study_id = ? ORDER BY created_at DESC",
                (study_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM insights ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


# --- Audit log -------------------------------------------------------------
def log_action(action: str, ai_value: dict, human_value: dict | None,
               insight_id: str | None = None, study_id: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO audit_log
               (insight_id, study_id, action, ai_value, human_value, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (insight_id, study_id, action,
             json.dumps(ai_value), json.dumps(human_value) if human_value else None,
             _now()),
        )


def list_audit_log() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
    return [dict(r) for r in rows]


# --- Search log (feeds reuse metric) ---------------------------------------
def log_search(query: str, returned_insight_ids: list[str]) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO search_log (query, returned_insight_ids, timestamp) VALUES (?, ?, ?)",
            (query, json.dumps(returned_insight_ids), _now()),
        )


def list_search_log() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM search_log ORDER BY timestamp DESC").fetchall()
    return [dict(r) for r in rows]
