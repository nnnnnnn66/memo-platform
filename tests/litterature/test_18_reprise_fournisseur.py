"""Une coupure PASSAGÈRE du fournisseur de modèle ne doit pas tuer une campagne.

Défaut réel, constaté en simulation complète : la revue de littérature avait lu 250 documents et
30 textes intégraux ; au moment de l'analyse, le fournisseur a rendu un 503, le client a levé
TOOL_ERROR sans réessayer, et 34 minutes de travail ont été perdues.

On vérifie donc ici :
  - qu'un 503 est RETENTÉ, et que l'appel finit par aboutir ;
  - qu'une erreur DÉFINITIVE (401) n'est PAS retentée — réessayer ne la guérirait pas et ferait
    perdre du temps à l'étudiant ;
  - que les reprises sont bornées (jamais de boucle infinie).
"""
import httpx
import pytest

from literature_review_agent.core.errors import ErrorState, PipelineError
from literature_review_agent.llm.client import LLMClient
from literature_review_agent.llm.client import _TENTATIVES


@pytest.fixture(autouse=True)
def _sans_attente(monkeypatch):
    """Les attentes réelles (3 s, 10 s) n'ont pas à être subies par la suite de tests."""
    monkeypatch.setattr("literature_review_agent.llm.client._ATTENTES", (0, 0))


def _limits():
    from literature_review_agent.core.limits import Limits

    return Limits(
        max_input_size=1000, max_output_tokens=100, max_agent_turns=1,
        max_verification_retries=1, timeout=5, max_llm_calls=10,
        max_search_queries=1, max_results_per_query=1, max_documents=1,
        min_documents_useful=1, max_external_requests=1, source_timeout=1,
        max_abstract_chars=10, documents_per_scoring_batch=1, max_scoring_batches=1,
        cache_ttl_hours=1, unpaywall_max_lookups=1, max_downloads=1, max_download_mb=1,
        max_session_download_mb=1, download_timeout=1, max_pdf_pages=1,
        max_text_chars_per_doc=1, max_excerpts_per_doc=1, excerpt_window_chars=1,
        max_quote_chars=1, max_thesis_resolvers=1, scoring_parallelism=1)


def _client(handler):
    creds = {"provider": "test", "base_url": "https://example.test/v1", "model": "m",
             "api_key": "x", "temperature": 0.2, "api_key_env": "X"}
    return LLMClient(creds, _limits(), transport=httpx.MockTransport(handler))


def test_un_503_est_retente_et_l_appel_aboutit():
    appels = {"n": 0}

    def handler(request):
        appels["n"] += 1
        if appels["n"] == 1:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = _client(handler)
    assert client.complete("sys", "user") == "ok"
    assert appels["n"] == 2, "le 503 aurait dû être retenté une fois"


def test_une_erreur_definitive_n_est_pas_retentee():
    appels = {"n": 0}

    def handler(request):
        appels["n"] += 1
        return httpx.Response(401, json={"error": "unauthorized"})

    client = _client(handler)
    with pytest.raises(PipelineError) as capture:
        client.complete("sys", "user")
    assert capture.value.state is ErrorState.TOOL_ERROR
    assert appels["n"] == 1, "un 401 ne guérira pas : le retenter est du temps perdu"


def test_un_503_persistant_echoue_apres_un_nombre_borne_de_tentatives():
    appels = {"n": 0}

    def handler(request):
        appels["n"] += 1
        return httpx.Response(503, json={"error": "unavailable"})

    client = _client(handler)
    with pytest.raises(PipelineError):
        client.complete("sys", "user")
    assert appels["n"] == _TENTATIVES, "les reprises doivent être bornées"
