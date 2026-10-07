"""Cache des requêtes de sources : reproductibilité, quotas, expiration."""

import time

from research_problem_agent.sources.cache import SourceCache


def test_enregistrement_et_relecture(tmp_path):
    cache = SourceCache(tmp_path / "cache.db", ttl_hours=168)
    records = [{"title": "T", "url": "https://doi.org/10.1/a"}]

    cache.set("openalex", "télétravail", 5, records)

    assert cache.get("openalex", "télétravail", 5) == records
    assert cache.hits == 1


def test_cle_normalisee_insensible_a_la_casse(tmp_path):
    cache = SourceCache(tmp_path / "cache.db", ttl_hours=168)
    cache.set("openalex", "Télétravail  Productivité", 5, [{"title": "T"}])

    assert cache.get("openalex", "télétravail  productivité", 5) == [{"title": "T"}]


def test_expiration_par_ttl(tmp_path):
    cache = SourceCache(tmp_path / "cache.db", ttl_hours=1)
    cache.set("openalex", "q", 5, [{"title": "T"}])

    # Vieillissement artificiel de l'entrée
    import sqlite3

    with sqlite3.connect(tmp_path / "cache.db") as con:
        con.execute("UPDATE sources_cache SET fetched_at = ?", (time.time() - 7200,))

    assert cache.get("openalex", "q", 5) is None
    assert cache.misses == 1


def test_absence_de_cache_compte_comme_manque(tmp_path):
    cache = SourceCache(tmp_path / "cache.db", ttl_hours=168)
    assert cache.get("openalex", "jamais vu", 5) is None
    assert cache.misses == 1
    assert cache.hits == 0
