"""Journal d'audit propre à l'agent (SQLite stdlib), filtré.

Aucun contenu du dossier ni donnée personnelle n'y est recopié : compteurs, statuts et verdict.
"""

import json
import sqlite3
import time
from pathlib import Path

from ..core.security_rules import redact

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_coherence (
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
    verdict TEXT,
    constats INTEGER,
    constats_bloqueurs INTEGER,
    constats_majeurs INTEGER,
    non_verifiable INTEGER,
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
              verdict: str = "", constats: int = 0, constats_bloqueurs: int = 0,
              constats_majeurs: int = 0, non_verifiable: int = 0, reformulations: int = 0,
              student_decision: str = "") -> None:
    erreurs = redact(json.dumps(errors or [], ensure_ascii=False))
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO audit_coherence (timestamp, session_id, agent_id, version, status, errors,"
            " validation_result, attempts, llm_calls, external_requests, cache_hits, document_status,"
            " verdict, constats, constats_bloqueurs, constats_majeurs, non_verifiable,"
            " reformulations, student_decision) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), session_id, agent_id, version, status, erreurs, validation_result,
             attempts, llm_calls, external_requests, cache_hits, document_status, verdict, constats,
             constats_bloqueurs, constats_majeurs, non_verifiable, reformulations, student_decision),
        )
