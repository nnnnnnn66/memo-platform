"""Journal d'audit (SQLite stdlib). Filtré : jamais de secret (SPEC §32)."""

import json
import sqlite3
import time
from pathlib import Path

from ..core.security_rules import redact

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
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
    source_ids TEXT
);
"""


def init(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute(_SCHEMA)


def log_event(db_path: Path, *, session_id: str, agent_id: str, version: str,
              status: str, errors=None, validation_result: str = "",
              attempts: int = 0, consumption: int = 0, source_ids=None) -> None:
    errors = redact(json.dumps(errors or [], ensure_ascii=False))
    source_ids = redact(json.dumps(source_ids or [], ensure_ascii=False))
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO audit (timestamp, session_id, agent_id, version, status, errors,"
            " validation_result, attempts, consumption, source_ids)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (time.time(), session_id, agent_id, version, status, errors,
             validation_result, attempts, consumption, source_ids),
        )
