"""Aides de test de l'Agent Problématique (aucun réseau, aucun coût).

Le module s'appelle `problematique_helpers` (jamais `helpers.py`) pour ne pas entrer en collision
avec `tests/helpers.py` quand toute la suite est lancée.
"""

import json

# --- corpus amont simulé (issu de l'étape 3) ---------------------------------------------------

DOC_A = {
    "doc_id": "D1",
    "title": "Télétravail et productivité des développeurs",
    "authors": ["Awa Traoré", "Jean Kouassi"],
    "year": 2023,
    "venue": "Revue africaine de gestion",
    "doi": "10.1234/rag.2023.001",
    "abstract": "Cette étude montre que le télétravail augmente la productivité des développeurs "
                "de 12 % dans les entreprises d'Abidjan. Les auteurs soulignent toutefois un effet "
                "hétérogène selon l'ancienneté.",
    "findings": [{"claim": "effet positif mesuré",
                  "quote": "le télétravail augmente la productivité des développeurs de 12 %"}],
    "full_text": {"downloaded": False, "text_layer": False},
}

DOC_B = {
    "doc_id": "D2",
    "title": "Télétravail et performance des équipes : une revue critique",
    "authors": ["Marie Dupont"],
    "year": 2021,
    "venue": "Journal of Work Studies",
    "doi": "10.5678/jws.2021.042",
    "abstract": "D'autres travaux ne retrouvent aucun effet significatif du télétravail sur la "
                "performance des équipes, ce qui contredit les résultats précédents.",
    "findings": [{"claim": "résultat contradictoire",
                  "quote": "aucun effet significatif du télétravail sur la performance des équipes"}],
    "full_text": {"downloaded": False, "text_layer": False},
}

QUOTE_A = "le télétravail augmente la productivité des développeurs de 12 % dans les entreprises"
QUOTE_B = "D'autres travaux ne retrouvent aucun effet significatif du télétravail sur la performance"
# Citation COURTE (25–60 caractères) volontairement inventée : elle repère le bug « fail-open ».
INVENTED_QUOTE = "une baisse de 37 % de la productivité a été mesurée"


def literature_payload(documents=None, verified=True, diagnosis=True):
    payload = {
        "agent": "literature_review_agent",
        "version": "1.0",
        "status": "ready_for_verification",
        "documents": documents if documents is not None else [dict(DOC_A), dict(DOC_B)],
        "validation": {"verified": verified, "verifier_status": "verified" if verified else "pending"},
    }
    if diagnosis:
        payload["diagnosis"] = {
            "matrix_row_id": "verify_theory",
            "reasoning_logic": "deductive",
            "research_type": "confirmatory",
            "approach": "quantitative",
            "techniques": ["enquête par questionnaire"],
        }
    return payload


# --- réponses simulées des phases LLM ----------------------------------------------------------

PROBLEM_MAPPING = {
    "agent": "problematization_agent",
    "version": "1.0",
    "problem_mapping": {
        "phenomene": "Le télétravail dans les entreprises de développement logiciel",
        "population": "développeurs d'Abidjan",
        "zone_geographique": "Abidjan, Côte d'Ivoire",
        "dysfonctionnement": "les délais ne sont plus tenus depuis le passage au télétravail",
        "provenance": "provided",
        "assumptions": [],
        "missing_elements": [],
        "clarification_questions": [],
    },
}

QUESTION_OBJECTIVES = {
    "agent": "problematization_agent",
    "version": "1.0",
    "research_question": {
        "question": "Dans quelle mesure le télétravail affecte-t-il la productivité des "
                    "développeurs d'Abidjan ?",
        "type": "ouverte explicative",
        "scope": "développeurs d'Abidjan",
        "status": "proposed",
    },
    "objectives": {
        "general": "Évaluer l'effet du télétravail sur la productivité des développeurs d'Abidjan.",
        "specifics": ["Mesurer la variation de productivité",
                      "Identifier les facteurs contextuels",
                      "Comparer les pratiques des entreprises"],
        "status": "proposed",
    },
}

VERIFIER_OK = {
    "agent": "problematique_verifier",
    "version": "1.0",
    "verdict": "verified",
    "controls": [{"code": "L1", "resultat": "ok", "detail": ""}],
    "corrections": [],
    "flags": [],
}

VERIFIER_CORRECTIONS = {
    "agent": "problematique_verifier",
    "version": "1.0",
    "verdict": "corrections_requested",
    "controls": [{"code": "L4", "resultat": "echec", "detail": "gap peu justifié"}],
    "corrections": ["Justifie le gap par une citation verbatim supplémentaire."],
    "flags": [],
}


def as_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


class StubLLM:
    """LLM simulé : dispatche les réponses selon la phase (marqueur du prompt système)."""

    def __init__(self, quote_mode: str = "anchored", verifier=None, corrections_once: bool = False):
        self.quote_mode = quote_mode
        self.verifier = verifier or VERIFIER_OK
        self.corrections_once = corrections_once
        self.calls = 0
        self._corrections_sent = 0

    # --- fabriques de sorties ---
    def _quote(self, anchored: str) -> str:
        return INVENTED_QUOTE if self.quote_mode == "invented" else anchored

    def confrontation(self) -> dict:
        return {
            "agent": "problematization_agent",
            "version": "1.0",
            "literature_confrontation": {
                "modeles_dominants": [
                    {"text": "Un effet positif du télétravail est mesuré", "doc_id": "D1",
                     "quote": self._quote(QUOTE_A), "section": "resume"}],
                "consensus": [],
                "divergences": [
                    {"text": "Un résultat contraire existe", "doc_id": "D2",
                     "quote": self._quote(QUOTE_B), "section": "resume"}],
                "concepts": ["télétravail", "productivité"],
                "statements": [],
            },
        }

    def gap(self) -> dict:
        return {
            "agent": "problematization_agent",
            "version": "1.0",
            "gap": {
                "type": "contextuelle",
                "description": "aucune étude n'a mesuré le télétravail dans les PME d'Abidjan",
                "justification": "les travaux recensés portent sur d'autres contextes",
                "statements": [
                    {"text": "La littérature documente d'autres contextes", "doc_id": "D1",
                     "quote": self._quote(QUOTE_A), "section": "resume"}],
                "gap_check": {"result": "unavailable", "queries": [], "publications": [], "note": ""},
            },
        }

    def justification(self) -> dict:
        return {
            "agent": "problematization_agent",
            "version": "1.0",
            "justification": {
                "texte": "Le télétravail transforme l'organisation du travail et ses effets "
                         "restent discutés selon les contextes.",
                "statements": [
                    {"text": "Un effet positif est mesuré dans un contexte proche", "doc_id": "D1",
                     "quote": self._quote(QUOTE_A), "section": "resume"},
                    {"text": "Un résultat contraire est documenté", "doc_id": "D2",
                     "quote": self._quote(QUOTE_B), "section": "resume"}],
            },
            "problematique_note": {
                "sections": [
                    "Problème réel constaté : les délais ne sont plus tenus à Abidjan.",
                    "État des savoirs : la littérature mesure des effets contrastés.",
                    "Rupture : aucune étude ne porte sur les PME d'Abidjan.",
                    "Justification scientifique : ce contexte reste inexploré.",
                    "Argumentaire : la problématique porte sur l'effet du télétravail à Abidjan.",
                ],
                "texte_complet": "Problème réel constaté : les délais ne sont plus tenus. "
                                 "État des savoirs : effets contrastés. Rupture : contexte "
                                 "ivoirien inexploré. Argumentaire : la problématique porte sur "
                                 "l'effet du télétravail à Abidjan.",
            },
        }

    def verifier_output(self) -> dict:
        if self.corrections_once and self._corrections_sent == 0:
            self._corrections_sent += 1
            return VERIFIER_CORRECTIONS
        return self.verifier

    # --- appel ---
    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        if "CARTOGRAPHIE DU PROBLÈME RÉEL" in system:
            return as_json(PROBLEM_MAPPING)
        if "CONFRONTATION LITTÉRAIRE" in system:
            return as_json(self.confrontation())
        if "IDENTIFICATION ET CLASSIFICATION DU GAP" in system:
            return as_json(self.gap())
        if "JUSTIFICATION SCIENTIFIQUE" in system:
            return as_json(self.justification())
        if "QUESTION DE RECHERCHE CANDIDATE" in system:
            return as_json(QUESTION_OBJECTIVES)
        if "VÉRIFICATEUR indépendant de l'Agent Problématique" in system:
            return as_json(self.verifier_output())
        raise AssertionError("StubLLM: prompt système non reconnu")


class FailLLM:
    """Modèle qui échoue : sert à tester les re-tentatives et les erreurs contrôlées."""

    def __init__(self, message: str = "boom"):
        self.calls = 0
        self.message = message

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self.message


# --- fausse couche réseau (gap check) ----------------------------------------------------------

OPENALEX_OK = {
    "results": [
        {"display_name": "Télétravail et productivité dans les PME d'Abidjan",
         "doi": "https://doi.org/10.9999/x", "publication_date": "2024-03-01",
         "authorships": [{"author": {"display_name": "A. Traoré"}}],
         "primary_location": {"source": {"display_name": "Revue africaine de gestion"}}},
    ]
}

CROSSREF_OK = {"message": {"items": []}}


class FakeFetcher:
    """Fetcher simulé : aucune socket, réponses programmées par URL."""

    def __init__(self, responses: dict, raise_for: set[str] | None = None):
        self.responses = responses
        self.raise_for = raise_for or set()
        self.requests = 0
        self.cfg = {}

    def fetch_json(self, url: str, params: dict | None = None, cost: int = 1,
                   headers: dict | None = None) -> dict:
        from problematization_agent.core.errors import ErrorState, PipelineError

        self.requests += 1
        for prefix in self.raise_for:
            if url.startswith(prefix):
                raise PipelineError(ErrorState.TOOL_ERROR, f"HTTP 429 simulé sur {url}")
        return self.responses.get(url, {})
