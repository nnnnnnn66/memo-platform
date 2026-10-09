"""Aides de test de l'Agent Objectifs de recherche (aucun réseau, aucun coût).

Le module s'appelle `objectifs_helpers` (jamais `helpers.py`) pour ne pas entrer en collision avec
`tests/helpers.py` quand toute la suite est lancée.
"""

import json


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu.

    `verdict` permet de tester la boucle de vérification (verified / corrections / rejected).
    `general`, `specific`, `analysis` permettent de fixer les sorties d'étage.
    """

    def __init__(self, verdict="verified", corrections=None, analysis=None, general=None,
                 specific=None):
        self.calls = 0
        self.verdict = verdict
        self.corrections = corrections or []
        self.analysis = analysis or DEFAULT_ANALYSIS
        self.general = general or DEFAULT_GENERAL
        self.specific = specific or DEFAULT_SPECIFIC
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "research_objectives_agent", "version": "1.0",
                    "question_analysis": self.analysis}
        elif "P2 —" in system:
            body = {"agent": "research_objectives_agent", "version": "1.0",
                    "general_objective": self.general}
        elif "P3 —" in system:
            body = {"agent": "research_objectives_agent", "version": "1.0", **self.specific}
        elif "Vérificateur" in system:
            body = {"agent": "objectives_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


DEFAULT_ANALYSIS = {
    "phenomene": "l'effet du télétravail sur la productivité",
    "action_attendue": "analyser",
    "dimensions": ["conditions de travail", "coordination des équipes", "mesure de la productivité"],
    "perimetre": "les développeurs d'Abidjan", "ambiguites": [], "provenance": "provided",
}
DEFAULT_GENERAL = ("Analyser la relation entre le télétravail et la productivité des développeurs "
                   "d'Abidjan afin d'en comprendre les conditions.")
DEFAULT_SPECIFIC = {
    "specific_objectives": [
        "Identifier les conditions de travail associées à la productivité en télétravail.",
        "Examiner l'effet de la coordination des équipes sur la productivité.",
        "Comparer la productivité observée selon les modalités de télétravail.",
    ],
    "objective_rationale": ("Ces objectifs décomposent la finalité principale et couvrent les "
                            "dimensions dégagées de la question."),
    "question_objective_alignment": {
        "general_to_question": "L'objectif général répond directement à la question principale.",
        "specifics_cover_general": "Les trois objectifs spécifiques décomposent l'objectif général.",
        "secondary_questions_coverage": [],
        "uncovered_dimensions": [],
    },
    "feasibility_assessment": {"verdict": "feasible", "raisons": ["données accessibles via enquête"],
                               "manques": []},
}


def upstream_question(verified=True, agent="research_question_agent"):
    """Sortie de l'Agent Question de recherche (étape 5), telle qu'elle est réellement produite."""
    return {
        "agent": agent,
        "version": "1.0",
        "status": "awaiting_human_validation",
        "subject": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "des développeurs ?",
        "secondary_research_questions": [],
        "validated_problematic": "La littérature montre un lien ambivalent entre télétravail et "
                                 "productivité.",
        "validation": {"verified": verified,
                       "verifier_status": "verified" if verified else "pending"},
    }
