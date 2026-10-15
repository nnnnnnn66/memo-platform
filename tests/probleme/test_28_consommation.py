"""Test 28 — consommation bornée : requêtes réseau plafonnées (SPEC §10.9)."""

import json

import pytest

from research_problem_agent.core.errors import ErrorState, PipelineError
from research_problem_agent.pipeline import sources_stage
from research_problem_agent.schemas.search_intent import SearchIntent
from research_problem_agent.sources.http import Fetcher


class _FakeResponse:
    """Réponse HTTP simulée : les tests restent hors réseau (déterministes, sans coût)."""

    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self, _n=None):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def no_network(monkeypatch):
    """Remplace l'ouverture réseau (redirections revalidées incluses) : rien ne sort."""
    calls = {"n": 0}

    def fake_open(check, request, timeout=None):
        calls["n"] += 1
        return _FakeResponse({"ok": True, "url": getattr(request, "full_url", "")})

    monkeypatch.setattr("research_problem_agent.sources.http.open_checked", fake_open)
    return calls


def test_fetcher_refuse_au_dela_du_budget(settings, no_network):
    fetcher = Fetcher(settings.sources, settings.limits, {"api.openalex.org"})
    for _ in range(settings.limits.max_external_requests):
        fetcher.fetch("https://api.openalex.org/works", {"search": "x"})

    with pytest.raises(PipelineError) as exc:
        fetcher.fetch("https://api.openalex.org/works", {"search": "y"})

    assert exc.value.state == ErrorState.RESOURCE_LIMIT
    assert fetcher.requests == settings.limits.max_external_requests
    assert no_network["n"] == settings.limits.max_external_requests  # aucune requête de trop


def test_stage_s_arrete_au_plafond_de_requetes(settings, monkeypatch):
    """Le nombre de requêtes exécutées ne dépasse jamais MAX_TOOL_CALLS."""
    settings.limits = type(settings.limits)(
        **{**{f: getattr(settings.limits, f) for f in settings.limits.__dataclass_fields__},
           "max_tool_calls": 2}
    )
    executed = {"n": 0}

    class _Registry:
        def allowed_hosts(self):
            return {"api.openalex.org"}

        def select(self, kind):
            from research_problem_agent.sources.registry import Provider
            return [Provider(id=f"p{i}", label=f"P{i}", family="publications",
                             source_type="scientific", host="api.openalex.org",
                             adapter="openalex") for i in range(6)]

        def adapter_module(self, provider):
            class _M:
                @staticmethod
                def search(fetcher, query, limit):
                    executed["n"] += 1
                    fetcher.requests += 1  # simule une requête réseau réellement effectuée
                    return [{"source": "P", "title": f"{provider.id}-{query}",
                             "url": f"https://doi.org/10.1/{provider.id}"}]
            return _M

    class _Cache:
        hits = 0
        misses = 0

        def get(self, *a):
            return None

        def set(self, *a):
            return None

    intents = [SearchIntent(query="télétravail productivité")]
    source_set = sources_stage.retrieve(intents, settings, registry=_Registry(),
                                        fetcher=Fetcher(settings.sources, settings.limits,
                                                        {"api.openalex.org"}),
                                        cache=_Cache())

    assert executed["n"] == 2
    assert len(source_set) == 2


def test_nombre_de_requetes_proposees_borne(settings):
    """MAX_SEARCH_QUERIES est appliqué côté métier (phase 1) — par TRONCATURE, sans échec.

    Le test décrivait l'ancien comportement (une violation levée, donc une campagne morte).
    Le code a raison de ne plus échouer : leçon du projet — corriger la surévaluation du modèle par
    le code, pas par un échec. On vérifie donc que la liste est ramenée à la borne, sans violation.
    """
    from probleme_helpers import phase1_output

    from research_problem_agent.pipeline import business_validation
    from research_problem_agent.schemas.search_intent import Phase1Output

    intents = [{"query": f"requête {i}", "kind": "publications"} for i in range(9)]
    phase1 = Phase1Output.model_validate(phase1_output(search_intents=intents))

    violations = business_validation.validate_phase1(phase1, settings.limits)
    assert len(phase1.search_intents) == settings.limits.max_search_queries
    assert not any("trop de requêtes" in v for v in violations)
