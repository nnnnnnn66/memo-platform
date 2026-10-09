"""Aides de test de l'Agent Diagnostic méthodologique (aucun réseau, aucun coût).

Le module s'appelle `methodologie_helpers` (jamais `helpers.py`) pour ne pas entrer en collision avec
`tests/helpers.py` quand toute la suite est lancée.
"""

import json


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu."""

    def __init__(self, verdict="verified", corrections=None, analysis=None, diagnosis=None):
        self.calls = 0
        self.verdict = verdict
        self.corrections = corrections or []
        self.analysis = analysis or DEFAULT_ANALYSIS
        self.diagnosis = diagnosis or DEFAULT_DIAGNOSIS
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "methodology_diagnostic_agent", "version": "1.0",
                    "analysis": self.analysis}
        elif "P2 —" in system:
            body = {"agent": "methodology_diagnostic_agent", "version": "1.0", **self.diagnosis}
        elif "Vérificateur" in system:
            body = {"agent": "methodology_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


DEFAULT_ANALYSIS = {
    "phenomene": "l'effet du télétravail sur la productivité",
    "visee": "examiner une relation entre deux variables dans un contexte donné",
    "nature_du_travail": "explicatif à visée de mesure de relation",
    "elements_disponibles": ["sujet", "question", "objectifs", "données de terrain annoncées"],
    "elements_manquants": [],
    "contradictions": [],
    "provenance": "provided",
}

DEFAULT_DIAGNOSIS = {
    "resume": "Le dossier porte sur la relation entre télétravail et productivité des salariés "
              "d'Abidjan, avec un terrain annoncé et des objectifs orientés vers la mesure d'un lien.",
    "diagnosis": {
        "approche": {"code": "quantitative",
                     "proposition": "Approche quantitative",
                     "justification": "La question et l'objectif portent sur une relation mesurable "
                                      "entre intensité du télétravail et productivité.",
                     "alternatives": ["approche mixte"], "conditions": ["échantillon suffisant"],
                     "limites": []},
        "logique": {"code": "hypothetico_deductive",
                    "proposition": "Démarche hypothético-déductive",
                    "justification": "Des hypothèses relationnelles peuvent être examinées par "
                                     "des mesures.",
                    "alternatives": [], "conditions": [], "limites": []},
        "type_recherche": {"code": "explicative",
                           "proposition": "Recherche explicative",
                           "justification": "Il s'agit d'expliquer la variation de la productivité "
                                            "selon les modalités de télétravail.",
                           "alternatives": ["descriptive"], "conditions": [], "limites": []},
        "strategie": {"code": "enquete",
                      "proposition": "Enquête par questionnaire auprès des salariés",
                      "justification": "Une enquête permet de recueillir des mesures comparables sur "
                                       "un ensemble de salariés.",
                      "alternatives": ["etude de cas"], "conditions": ["accès confirmé au terrain"],
                      "limites": ["biais de déclaration"]},
        "collecte": [{"code": "", "proposition": "Questionnaire structuré",
                      "justification": "Permet de mesurer l'intensité du télétravail et la "
                                       "productivité perçue.",
                      "alternatives": [], "conditions": [], "limites": []}],
        "analyse": [{"code": "", "proposition": "Analyse statistique descriptive et corrélation",
                     "justification": "Adaptée à des variables mesurées et à l'examen d'une relation.",
                     "alternatives": [], "conditions": [], "limites": []}],
        "articulation": "L'enquête alimente une analyse de corrélation, cohérente avec l'approche "
                        "quantitative et la logique hypothético-déductive.",
        "coherence_question": "La mesure du lien et son degré répondent directement à la question.",
    },
    "hypotheses_examined": [],
    "feasibility_controls": ["terrain annoncé accessible", "ressources limitées mais suffisantes"],
    "limits_of_this_output": [],
    "questions_for_human": ["Confirmer la possibilité de mesurer la productivité."],
}


def upstream_hypotheses(verified=True, agent="research_hypotheses_agent", with_hypotheses=True):
    """Sortie de l'Agent Hypothèses (étape 7), telle qu'elle est réellement produite."""
    hypotheses = []
    if with_hypotheses:
        hypotheses = [{"id": "H1", "formulation": "La coordination des équipes est associée à la "
                                                  "productivité des salariés en télétravail."}]
    return {
        "agent": agent,
        "version": "1.0",
        "status": "awaiting_human_validation",
        "subject": "Le télétravail et la productivité des salariés à Abidjan, 2020-2024",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "des salariés ?",
        "general_objective": "Analyser la relation entre le télétravail et la productivité.",
        "specific_objectives": ["Identifier les conditions de travail associées à la productivité."],
        "hypotheses_decision": "HYPOTHESES_RECOMMENDED",
        "research_hypotheses": hypotheses,
        "validation": {"verified": verified,
                       "verifier_status": "verified" if verified else "pending"},
    }


def upstream_agents_5_7(verified=True, with_hypotheses=True):
    """Forme RÉELLE des sorties des agents 5 à 7 : `verification_result`, PAS de clé `validation`.

    C'est exactement ce que produisent `question_output.json`, `objectives_output.json` et
    `hypotheses_output.json` (constaté sur disque). Un contrat d'entrée qui n'accepte que
    `validation` déclare ces sorties « non vérifiées » — bug de chaîne réel (mêmes symptômes que
    la passation 3 -> 4 : la sortie existait mais n'arrivait pas).
    """
    payload = upstream_hypotheses(verified=verified, with_hypotheses=with_hypotheses)
    payload.pop("validation", None)
    payload["status"] = "validated"
    payload["verification_result"] = {"verified": verified,
                                      "verifier_status": "verified" if verified else "pending"}
    return payload
