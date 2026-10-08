"""Aides de test de l'Agent Question de recherche (aucun réseau, aucun coût).

Le module s'appelle `question_helpers` (jamais `helpers.py`) pour ne pas entrer en collision avec
`tests/helpers.py` quand toute la suite est lancée.
"""

import json


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu.

    `verdict` permet de tester la boucle de vérification (verified / corrections / rejected).
    `answers` permet de remplacer une réponse d'étage par un JSON brut (pour tester les dégradés).
    """

    def __init__(self, verdict="verified", corrections=None, question=None,
                 comprehension=None, intention=None, formulation=None):
        self.calls = 0
        self.verdict = verdict
        self.corrections = corrections or []
        self.question = question or DEFAULT_QUESTION
        self.comprehension = comprehension or DEFAULT_COMPREHENSION
        self.intention = intention or DEFAULT_INTENTION
        self.formulation_override = formulation
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "research_question_agent", "version": "1.0",
                    "comprehension": self.comprehension}
        elif "P2 —" in system:
            body = {"agent": "research_question_agent", "version": "1.0",
                    "research_intention": self.intention}
        elif "P3 —" in system:
            formulation = self.formulation_override or {}
            body = {
                "agent": "research_question_agent", "version": "1.0",
                "main_research_question": formulation.get("main", self.question),
                "secondary_research_questions": formulation.get("secondary", []),
                "formulation_rationale": formulation.get(
                    "rationale", "La question découle de la problématique et reste neutre."),
                "scope_and_boundaries": formulation.get(
                    "scope", {"geo": "", "temps": "", "population": ""}),
                "feasibility_assessment": formulation.get(
                    "feasibility", {"verdict": "feasible", "raisons": ["données accessibles"],
                                    "manques": []}),
            }
        elif "Vérificateur" in system:
            body = {"agent": "question_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


DEFAULT_QUESTION = ("Dans quelle mesure le télétravail influence-t-il la productivité des "
                    "développeurs ?")
DEFAULT_COMPREHENSION = {
    "phenomene": "l'effet du télétravail sur la productivité",
    "objet_central": "le lien entre télétravail et productivité",
    "population": "développeurs", "zone": "Abidjan", "periode": "2020-2024",
    "reste_a_examiner": "la nature et l'ampleur du lien", "provenance": "provided",
}
DEFAULT_INTENTION = {
    "intention": "expliquer",
    "justification": "La problématique interroge la nature du lien : il s'agit d'expliquer.",
    "alternatives": [],
}


def problematique_note():
    return ("Le télétravail s'est diffusé massivement et son effet sur la productivité reste discuté. "
            "Les travaux divergent : certains mesurent un gain, d'autres une baisse. Cette tension "
            "constitue le cœur de la problématique.")


def upstream_problematic(verified=True, agent="problematization_agent"):
    """Sortie de l'Agent Problématique (étape 4), telle qu'elle est réellement produite."""
    return {
        "agent": agent,
        "version": "1.0",
        "status": "ready_for_verification",
        "subject_reference": {
            "original": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
            "reformulated": "Effets du télétravail sur la productivité des développeurs d'Abidjan",
        },
        "problematique_note": {"sections": ["probleme_reel", "etat_des_savoirs"],
                               "texte_complet": problematique_note()},
        "validation": {"verified": verified, "verifier_status": "verified" if verified else "pending"},
    }
