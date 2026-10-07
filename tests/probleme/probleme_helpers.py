"""Aides de test de l'Agent Problème (zéro coût : LLM simulé déterministe)."""

import json

PHASE1_READY = {
    "agent": "research_problem_agent",
    "version": "1.0",
    "preliminary_analysis": {
        "phenomenon": "effets du télétravail sur la productivité",
        "population": "développeurs",
        "context": "entreprise de services numériques",
        "geographical_scope": "Abidjan",
        "temporal_scope": "2020-2024",
        "main_concepts": ["télétravail", "productivité"],
    },
    "needs_search": True,
    "search_intents": [
        {"query": "télétravail productivité", "purpose": "preuves empiriques",
         "kind": "publications", "language": "fr"}
    ],
}

VERIFIER_VERIFIED = {
    "agent": "research_problem_verifier",
    "version": "1.0",
    "verdict": "verified",
    "controls": [{"code": "V1", "resultat": "ok", "detail": ""}],
    "corrections": [],
    "flags": [],
}

VERIFIER_CORRECTIONS = {
    "agent": "research_problem_verifier",
    "version": "1.0",
    "verdict": "corrections_requested",
    "controls": [{"code": "V8", "resultat": "echec", "detail": "inconnues non signalées"}],
    "corrections": ["V8: signaler explicitement les informations inconnues"],
    "flags": [],
}

VERIFIER_REJECTED = {
    "agent": "research_problem_verifier",
    "version": "1.0",
    "verdict": "rejected",
    "controls": [{"code": "V5", "resultat": "echec", "detail": "source inexistante"}],
    "corrections": [],
    "flags": ["référence inventée"],
}


def problem_output(subject_text, status="ready_for_verification", **overrides):
    """Fiche conforme minimale ; les tests surchargent ce qui les intéresse."""
    out = {
        "agent": "research_problem_agent",
        "version": "1.0",
        "status": status,
        "subject_reference": {"original": subject_text, "reformulated": ""},
        "identified_problem": {
            "statement": "Le télétravail dégrade la productivité perçue des développeurs.",
            "situation": "Passage massif au travail à distance depuis 2020.",
            "why_problematic": "Les effets réels sur la productivité sont discutés.",
            "actors_concerned": ["développeurs", "employeurs"],
            "consequences": ["baisse de productivité perçue"],
            "stakes": ["organisation du travail"],
        },
        "justifying_elements": [
            {"element": "Le passage au télétravail a été massif en 2020.",
             "source_id": "", "provenance": "provided", "nature": "fact"},
        ],
        "sources": [],
        "unknown_information": ["ampleur réelle du phénomène à Abidjan"],
        "gaps": ["absence de séries locales"],
        "remaining_questions": ["Quel périmètre d'entreprise ?"],
        "provisional_formulation": (
            "Le problème porte sur les effets du télétravail sur la productivité des "
            "développeurs, encore discutés."
        ),
        "delimitation": {"population": "développeurs", "geographical_scope": "Abidjan",
                         "temporal_scope": "2020-2024", "context": "services numériques"},
        "search_queries_used": [],
        "confidence": {"overall": 0.5, "rationale": "informations partielles"},
        "validation": {"verified": False, "verifier_status": "pending"},
    }
    out.update(overrides)
    return out


def phase1_output(**overrides):
    out = json.loads(json.dumps(PHASE1_READY))
    out.update(overrides)
    return out


def as_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


class StubLLM:
    """LLM simulé : renvoie une file de réponses prédéfinies. Reproductible, sans réseau."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.sent = []

    def complete(self, system, user):
        self.sent.append({"system": system, "user": user})
        if not self.responses:
            raise AssertionError("StubLLM: plus de réponses disponibles")
        self.calls += 1
        return self.responses.pop(0)


class FakeFetcher:
    """Client HTTP simulé : réponses enregistrées, aucune sortie réseau."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.requests = 0
        self.bytes_downloaded = 0
        self.errors = []
        self.seen = []

    def _match(self, url: str):
        for fragment, payload in self.responses.items():
            if fragment in url:
                return payload
        raise AssertionError(f"FakeFetcher: aucune réponse enregistrée pour {url}")

    def fetch(self, url: str, params=None) -> str:
        self.requests += 1
        self.seen.append(url)
        payload = self._match(url)
        return payload if isinstance(payload, str) else json.dumps(payload)

    def fetch_json(self, url: str, params=None) -> dict:
        payload = self._match(url)
        self.requests += 1
        self.seen.append(url)
        if isinstance(payload, str):
            return json.loads(payload)
        return payload


def source_set_with(records):
    """Construit un SourceSet à partir de dicts normalisés (source_id attribué dans l'ordre)."""
    from research_problem_agent.sources.source_set import SourceSet

    source_set = SourceSet()
    for item in records:
        source_set.add(item.get("provider", "openalex"), item,
                       item.get("source_type", "scientific"),
                       item.get("snippet_limit", 1200))
        if item.get("provider"):
            pass
    return source_set
