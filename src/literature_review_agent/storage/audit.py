"""Journal d'audit propre à l'agent (SQLite stdlib), filtré."""

import json
import sqlite3
import time
from pathlib import Path

from ..core.security_rules import redact

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_litterature (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    session_id TEXT,
    agent_id TEXT,
    version TEXT,
    status TEXT,
    errors TEXT,
    validation_result TEXT,
    attempts INTEGER,
    llm_calls INTEGER,
    external_requests INTEGER,
    cache_hits INTEGER,
    providers_used TEXT,
    documents_count INTEGER,
    downloaded_count INTEGER,
    source_ids TEXT
);
"""


def init(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute(_SCHEMA)


def log_event(db_path: Path, *, session_id: str, agent_id: str, version: str, status: str,
              errors=None, validation_result: str = "", attempts: int = 0, llm_calls: int = 0,
              external_requests: int = 0, cache_hits: int = 0, providers_used=None,
              documents_count: int = 0, downloaded_count: int = 0, source_ids=None) -> None:
    errors = redact(json.dumps(errors or [], ensure_ascii=False))
    providers_used = redact(json.dumps(providers_used or [], ensure_ascii=False))
    source_ids = redact(json.dumps(source_ids or [], ensure_ascii=False))
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO audit_litterature (timestamp, session_id, agent_id, version, status,"
            " errors, validation_result, attempts, llm_calls, external_requests, cache_hits,"
            " providers_used, documents_count, downloaded_count, source_ids)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), session_id, agent_id, version, status, errors, validation_result,
             attempts, llm_calls, external_requests, cache_hits, providers_used,
             documents_count, downloaded_count, source_ids),
        )
