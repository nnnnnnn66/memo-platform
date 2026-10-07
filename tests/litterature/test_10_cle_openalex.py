"""Clé OpenAlex (agent 3) : lue dans l'environnement, transmise en EN-TÊTE, jamais dans l'URL.

Régressions visées :
- l'adaptateur de l'agent 3 ne lisait aucune clé, donc subissait le `429` d'OpenAlex partagé
  par adresse IP (l'agent 4 avait déjà ce support) ;
- une clé ne doit jamais finir dans une URL (journalisée et recopiée dans les erreurs).
"""

from litterature_helpers import FakeApiFetcher, openalex_payload

from literature_review_agent.sources.adapters import openalex

URL = "https://api.openalex.org/works"
CLE = "cle-secrete-123"


def _fetcher():
    return FakeApiFetcher({URL: openalex_payload()})


def test_cle_envoyee_en_entete_authorization(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", CLE)
    fetcher = _fetcher()

    openalex.search(fetcher, "télétravail", 5)

    assert fetcher.last_headers.get("Authorization") == f"Bearer {CLE}"


def test_cle_jamais_dans_l_url(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", CLE)
    fetcher = _fetcher()

    openalex.search(fetcher, "télétravail", 5)

    assert fetcher.seen, "la requête doit avoir été émise"
    assert all(CLE not in url for url in fetcher.seen)


def test_sans_cle_requete_anonyme(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    fetcher = _fetcher()

    openalex.search(fetcher, "télétravail", 5)

    assert "Authorization" not in fetcher.last_headers
