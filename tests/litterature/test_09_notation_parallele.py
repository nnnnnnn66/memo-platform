"""Notation/extraction par lots EN PARALLÈLE — garanties d'identité et de bornes.

La vitesse ne doit jamais se payer en qualité : ces tests vérifient que noter les lots en parallèle
(1) produit EXACTEMENT les mêmes analyses qu'en séquentiel, (2) borne bien le nombre d'appels
simultanés, et (3) que le plafond d'appels LLM reste vrai quand plusieurs fils appellent le client.
"""

import dataclasses
import json
import re
import threading
import time

from litterature_helpers import as_json

from literature_review_agent.core.errors import ErrorState, PipelineError
from literature_review_agent.pipeline import scoring_stage
from literature_review_agent.sources.corpus import Corpus, CorpusRecord


def _corpus(n: int) -> Corpus:
    corpus = Corpus()
    for i in range(n):
        corpus.add(CorpusRecord(
            provider="crossref", source_type="scientific", document_type="article",
            title=f"Telework and productivity study {i}",
            url=f"https://doi.org/10.{i}/x", doi=f"10.{i}/x",
            authors=["Jane Doe"], year=2021, language="en",
            abstract=(f"telework productivity evidence for case {i}: a positive but "
                      "heterogeneous effect was measured over one year."),
        ))
    return corpus


class BatchStubLLM:
    """Répond à la phase de notation en renvoyant une analyse par doc_id du lot.

    Enregistre la concurrence observée (pour prouver que les lots tournent bien en parallèle) et
    simule un temps de réponse pour rendre le chevauchement observable.
    """

    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.calls = 0
        self.concurrent = 0
        self.max_concurrent = 0
        self._lock = threading.Lock()

    def complete(self, system: str, user: str) -> str:
        with self._lock:
            self.calls += 1
            self.concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent)
        try:
            if self.delay:
                time.sleep(self.delay)
            ids = list(dict.fromkeys(re.findall(r"\[(D\d+)\]", user)))
            return as_json({
                "agent": "literature_review_agent", "version": "1.0",
                "documents": [
                    {"doc_id": doc_id, "relevance": 0.7, "theme": "télétravail",
                     "method": "enquête", "field_site": "entreprises",
                     "extraction_scope": "abstract_only", "findings": [], "limits": []}
                    for doc_id in ids
                ],
            })
        finally:
            with self._lock:
                self.concurrent -= 1


def _limits(settings, parallelism: int):
    return dataclasses.replace(settings.limits, documents_per_scoring_batch=1,
                               max_scoring_batches=4, scoring_parallelism=parallelism)


def _with_parallelism(settings, parallelism: int):
    """Applique des bornes de test (petits lots) et le parallélisme voulu."""
    settings.limits = _limits(settings, parallelism)
    return settings


def test_parallele_produit_les_memes_analyses_que_sequentiel(settings, request_factory):
    """Mêmes documents, mêmes analyses, même nombre de tentatives : seul l'ordre change."""
    request = request_factory()
    corpus = _corpus(4)

    seq_llm = BatchStubLLM()
    seq_analyses, seq_attempts = scoring_stage.run(
        seq_llm, request, corpus, {}, [], _with_parallelism(settings, 1))

    par_llm = BatchStubLLM()
    par_analyses, par_attempts = scoring_stage.run(
        par_llm, request, corpus, {}, [], _with_parallelism(settings, 4))

    assert par_analyses == seq_analyses
    assert par_attempts == seq_attempts
    assert set(par_analyses) == {r.doc_id for r in corpus.records}
    # L'ordre d'insertion reste celui des lots, comme en séquentiel (résultat déterministe).
    assert list(par_analyses) == list(seq_analyses)


def test_lots_executes_simultanement(settings, request_factory):
    """La parallélisation doit être RÉELLE : plusieurs appels LLM se chevauchent."""
    request = request_factory()
    corpus = _corpus(4)
    llm = BatchStubLLM(delay=0.2)

    scoring_stage.run(llm, request, corpus, {}, [], _with_parallelism(settings, 3))

    assert llm.max_concurrent >= 2, "les lots ne se sont pas chevauchés"


def test_parallellisme_borne(settings, request_factory):
    """Le nombre d'appels simultanés ne dépasse jamais la borne configurée."""
    request = request_factory()
    corpus = _corpus(4)
    llm = BatchStubLLM(delay=0.2)

    scoring_stage.run(llm, request, corpus, {}, [], _with_parallelism(settings, 2))

    assert llm.max_concurrent <= 2


def test_echec_d_un_lot_fait_echouer_la_campagne(settings, request_factory):
    """Un lot définitivement invalide doit lever, comme en séquentiel (jamais de faux succès)."""
    request = request_factory()
    corpus = _corpus(4)

    class BadLLM(BatchStubLLM):
        def complete(self, system, user):
            super().complete(system, user)
            return "pas de JSON ici"

    try:
        scoring_stage.run(BadLLM(), request, corpus, {}, [], _with_parallelism(settings, 4))
    except PipelineError as exc:
        assert exc.state == ErrorState.OUTPUT_SCHEMA_ERROR
    else:  # pragma: no cover - le test échoue si aucune erreur n'est levée
        raise AssertionError("un lot invalide n'a pas fait échouer la notation")


# --- plafond du client LLM réel sous concurrence -------------------------------------------------

def _llm_client(max_calls: int):
    import httpx

    from literature_review_agent.core.limits import Limits
    from literature_review_agent.llm.client import LLMClient

    def handler(request: httpx.Request) -> httpx.Response:
        time.sleep(0.01)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"completion_tokens": 1},
        })

    limits = Limits(
        max_input_size=1000, max_output_tokens=100, max_agent_turns=1,
        max_verification_retries=1, timeout=5, max_llm_calls=max_calls,
        max_search_queries=1, max_results_per_query=1, max_documents=1,
        min_documents_useful=1, max_external_requests=1, source_timeout=1,
        max_abstract_chars=10, documents_per_scoring_batch=1, max_scoring_batches=1,
        cache_ttl_hours=1, unpaywall_max_lookups=1, max_downloads=1, max_download_mb=1,
        max_session_download_mb=1, download_timeout=1, max_pdf_pages=1,
        max_text_chars_per_doc=1, max_excerpts_per_doc=1, excerpt_window_chars=1,
        max_quote_chars=1, max_thesis_resolvers=1, scoring_parallelism=4)
    creds = {"provider": "test", "base_url": "https://example.test/v1", "model": "m",
             "api_key": "x", "temperature": 0.2, "api_key_env": "X"}
    return LLMClient(creds, limits, transport=httpx.MockTransport(handler))


def test_plafond_appels_llm_vrai_en_concurrence():
    """Sans verrou, plusieurs fils lisaient le même compteur avant de l'incrémenter.

    Ici 12 fils lancent chacun 2 appels (24 tentatives) avec un plafond de 5 : le client doit en
    accepter EXACTEMENT 5, jamais plus — la qualité d'arrêt ne dépend pas du hasard de l'ordonnancement.
    """
    client = _llm_client(max_calls=5)
    reussis = []
    erreurs = []
    lock = threading.Lock()

    def worker():
        for _ in range(2):
            try:
                client.complete("system", "user")
                with lock:
                    reussis.append(1)
            except PipelineError as exc:
                with lock:
                    erreurs.append(exc.state)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert client.calls == 5
    assert len(reussis) == 5
    assert all(state == ErrorState.RESOURCE_LIMIT for state in erreurs)


def test_nouvelle_campagne_remet_le_compteur_a_zero():
    client = _llm_client(max_calls=1)
    client.complete("s", "u")
    try:
        client.complete("s", "u")
    except PipelineError:
        pass
    client.nouvelle_campagne()
    assert client.calls == 0
    client.complete("s", "u")
    assert client.calls == 1
