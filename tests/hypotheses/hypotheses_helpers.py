"""Aides de test de l'Agent Hypothèses de recherche (aucun réseau, aucun coût).

Le module s'appelle `hypotheses_helpers` (jamais `helpers.py`) pour ne pas entrer en collision avec
`tests/helpers.py` quand toute la suite est lancée.
"""

import json


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu."""

    def __init__(self, verdict="verified", corrections=None, analysis=None, decision=None,
                 decision_rationale=None, clarification_questions=None, formulation=None):
        self.calls = 0
        self.verdict = verdict
        self.corrections = corrections or []
        self.analysis = analysis or DEFAULT_ANALYSIS
        self.decision = decision or "HYPOTHESES_RECOMMENDED"
        self.decision_rationale = decision_rationale or (
            "La question porte sur une relation mesurable : des hypothèses formelles sont pertinentes.")
        self.clarification_questions = clarification_questions or []
        self.formulation = formulation or DEFAULT_FORMULATION
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "research_hypotheses_agent", "version": "1.0",
                    "analysis": self.analysis}
        elif "P2 —" in system:
            body = {"agent": "research_hypotheses_agent", "version": "1.0",
                    "hypotheses_decision": self.decision,
                    "decision_rationale": self.decision_rationale,
                    "clarification_questions": list(self.clarification_questions)}
        elif "P3 —" in system:
            body = {"agent": "research_hypotheses_agent", "version": "1.0", **self.formulation}
        elif "Vérificateur" in system:
            body = {"agent": "hypotheses_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


DEFAULT_ANALYSIS = {
    "phenomene": "l'effet du télétravail sur la productivité",
    "action_attendue": "expliquer / mesurer une relation",
    "nature_du_travail": "explicatif",
    "ambiguites": [], "provenance": "provided",
}
DEFAULT_FORMULATION = {
    "research_hypotheses": [
        {
            "id": "H1",
            "formulation": "Une meilleure coordination des équipes est associée à une productivité "
                           "plus élevée des développeurs en télétravail.",
            "linked_to": "Objectif général",
            "concepts_variables": ["coordination des équipes", "productivité"],
            "justification": "La problématique souligne le rôle de la coordination lorsque le "
                             "télétravail se développe.",
            "sources": ["problématique fournie"],
            "required_data": ["indicateur de coordination", "mesure de productivité"],
            "limits": [],
        },
        {
            "id": "H2",
            "formulation": "L'intensité du télétravail est associée à une variation de la "
                           "productivité selon les conditions de travail.",
            "linked_to": "Objectif spécifique 1",
            "concepts_variables": ["intensité du télétravail", "conditions de travail"],
            "justification": "La littérature fournie signale des résultats divergents selon les "
                             "contextes de travail.",
            "sources": ["littérature fournie"],
            "required_data": ["nombre de jours en télétravail", "mesure de productivité"],
            "limits": [],
        },
    ],
    "hypothesis_objective_alignment": {
        "general_to_objectives": "L'objectif général vise à analyser la relation ; les hypothèses "
                                 "en explicitent les relations attendues.",
        "hypotheses_cover_objectives": "H1 couvre la coordination, H2 l'intensité et les conditions.",
        "uncovered_objectives": [],
        "contradictions": [],
    },
    "theoretical_or_literature_support": ["problématique fournie", "littérature fournie"],
    "required_evidence": ["mesure de productivité", "indicateur de coordination"],
}


def upstream_objectives(verified=True, agent="research_objectives_agent"):
    """Sortie de l'Agent Objectifs de recherche (étape 6), telle qu'elle est réellement produite.

    Attention : l'agent 6 publie la vérification sous `verification_result` (comme les agents 5 et 7),
    PAS sous `validation`. Un fixture bâti sur `validation` faisait passer les tests alors que la
    passation 6 -> 7 échouait en exécution réelle.
    """
    return {
        "agent": agent,
        "version": "1.0",
        "status": "awaiting_human_validation",
        "subject": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "des développeurs ?",
        "general_objective": "Analyser la relation entre le télétravail et la productivité des "
                             "développeurs.",
        "specific_objectives": ["Identifier les conditions de travail associées à la productivité.",
                                "Examiner l'effet de la coordination des équipes."],
        "verification_result": {"verified": verified,
                                "verifier_status": "verified" if verified else "pending"},
    }
