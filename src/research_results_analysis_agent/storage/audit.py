"""Journal d'audit propre à l'agent (SQLite stdlib), filtré.

Aucune donnée brute de l'étudiant n'est recopiée : seuls des compteurs et des statuts.
"""

import json
import sqlite3
import time
from pathlib import Path

from ..core.security_rules import redact

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_resultats (
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
    document_status TEXT,
    calculs INTEGER,
    hypotheses INTEGER,
    reformulations INTEGER,
    student_decision TEXT
);
"""


def init(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute(_SCHEMA)


def log_event(db_path: Path, *, session_id: str, agent_id: str, version: str, status: str,
              errors=None, validation_result: str = "", attempts: int = 0, llm_calls: int = 0,
              external_requests: int = 0, cache_hits: int = 0, document_status: str = "",
              calculs: int = 0, hypotheses: int = 0, reformulations: int = 0,
              student_decision: str = "") -> None:
    errors = redact(json.dumps(errors or [], ensure_ascii=False))
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO audit_resultats (timestamp, session_id, agent_id, version, status,"
            " errors, validation_result, attempts, llm_calls, external_requests, cache_hits,"
            " document_status, calculs, hypotheses, reformulations, student_decision)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), session_id, agent_id, version, status, errors, validation_result,
             attempts, llm_calls, external_requests, cache_hits, document_status, calculs,
             hypotheses, reformulations, student_decision),
        )
