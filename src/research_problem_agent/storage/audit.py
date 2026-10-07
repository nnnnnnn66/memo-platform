"""Journal d'audit propre à l'agent (SQLite stdlib). Filtré : jamais de secret (SPEC §10.11)."""

import json
import sqlite3
import time
from pathlib import Path

from ..core.security_rules import redact

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_probleme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    session_id TEXT,
    agent_id TEXT,
    version TEXT,
    status TEXT,
    errors TEXT,
    validation_result TEXT,
    attempts INTEGER,
    consumption INTEGER,
    external_requests INTEGER,
    cache_hits INTEGER,
    providers_used TEXT,
    source_ids TEXT
);
"""


def init(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute(_SCHEMA)


def log_event(db_path: Path, *, session_id: str, agent_id: str, version: str,
              status: str, errors=None, validation_result: str = "",
              attempts: int = 0, consumption: int = 0, external_requests: int = 0,
              cache_hits: int = 0, providers_used=None, source_ids=None) -> None:
    errors = redact(json.dumps(errors or [], ensure_ascii=False))
    providers_used = redact(json.dumps(providers_used or [], ensure_ascii=False))
    source_ids = redact(json.dumps(source_ids or [], ensure_ascii=False))
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO audit_probleme (timestamp, session_id, agent_id, version, status,"
            " errors, validation_result, attempts, consumption, external_requests, cache_hits,"
            " providers_used, source_ids) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), session_id, agent_id, version, status, errors,
             validation_result, attempts, consumption, external_requests, cache_hits,
             providers_used, source_ids),
        )
