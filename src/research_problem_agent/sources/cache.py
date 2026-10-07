"""Cache SQLite des requêtes de sources : reproductibilité, quotas, tests hors réseau.

Réutilise `sqlite3` de la stdlib : aucune dépendance, aucun coût, aucune base vectorielle.
"""

import json
import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources_cache (
    key TEXT PRIMARY KEY,
    provider TEXT,
    query TEXT,
    payload TEXT,
    fetched_at REAL
);
"""


class SourceCache:
    def __init__(self, db_path: Path, ttl_hours: int) -> None:
        self.db_path = Path(db_path)
        self.ttl_seconds = int(ttl_hours) * 3600
        self.hits = 0
        self.misses = 0
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as con:
            con.execute(_SCHEMA)

    @staticmethod
    def key(provider: str, query: str, limit: int) -> str:
        return f"{provider}|{query.strip().lower()}|{limit}"

    def get(self, provider: str, query: str, limit: int):
        key = self.key(provider, query, limit)
        with sqlite3.connect(self.db_path) as con:
            row = con.execute(
                "SELECT payload, fetched_at FROM sources_cache WHERE key = ?", (key,)
            ).fetchone()
        if not row:
            self.misses += 1
            return None
        payload, fetched_at = row
        if self.ttl_seconds and (time.time() - fetched_at) > self.ttl_seconds:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(payload)

    def set(self, provider: str, query: str, limit: int, records: list[dict]) -> None:
        key = self.key(provider, query, limit)
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "INSERT OR REPLACE INTO sources_cache (key, provider, query, payload, fetched_at)"
                " VALUES (?,?,?,?,?)",
                (key, provider, query, json.dumps(records, ensure_ascii=False), time.time()),
            )
