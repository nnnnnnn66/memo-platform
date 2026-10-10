"""Aides de test de l'Agent Conclusion (aucun réseau, aucun coût).

Les fixtures copient la forme RÉELLE des sorties amont (leçon de la chaîne 1 → 10) : la sortie de
l'étape 10 est reproduite avec ses `computed_results` (identifiants `R…`), son `plan` (résultats
retenus, hypothèses examinées) et sa `synthese_pour_conclusion`.
"""

import json


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu."""

    def __init__(self, verdict="verified", corrections=None, synthesis=None, plan=None, draft=None):
        self.calls = 0
        self.verdict = verdict
        self.corrections = corrections or []
        self.synthesis = synthesis or DEFAULT_SYNTHESIS
        self.plan = plan or DEFAULT_PLAN
        self.draft = draft or DEFAULT_DRAFT
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "research_conclusion_agent", "version": "1.0",
                    "synthesis": self.synthesis}
        elif "P2 —" in system:
            body = {"agent": "research_conclusion_agent", "version": "1.0", "plan": self.plan}
        elif "P3 —" in system:
            body = {"agent": "research_conclusion_agent", "version": "1.0", "draft": self.draft}
        elif "Vérificateur" in system:
            body = {"agent": "conclusion_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


def upstream_question(verified=True):
    return {
        "agent": "research_question_agent", "status": "validated",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "déclarée des développeurs ?",
        "secondary_research_questions": [],
        "verification_result": {"verified": verified,
                                "verifier_status": "verified" if verified else "pending"},
    }


def upstream_results(verified=True, status="valide", accepted=True, plan_seulement=False,
                     hypotheses=None):
    """Forme RÉELLE de la sortie de l'étape 10 (`verification_result`, `computed_results`, `plan`)."""
    computed = [] if plan_seulement else [
        {"id": "R1", "libelle": "nombre de lignes analysées", "valeur": "20", "unite": "",
         "effectif": 20, "methode": "effectif_total", "variable": "", "groupe": ""},
        {"id": "R2", "libelle": "moyenne — productivite_declaree", "valeur": "6,15", "unite": "",
         "effectif": 20, "methode": "moyenne", "variable": "productivite_declaree", "groupe": ""},
    ]
    return {
        "agent": "research_results_analysis_agent", "version": "1.0",
        "status": "awaiting_human_validation",
        "document_status": status,
        "verification_result": {"verified": verified,
                                "verifier_status": "verified" if verified else "pending"},
        "student_validation": {"decision": "accepted" if accepted else None, "comment": ""},
        "computed_results": {"resultats": computed, "notes": []},
        "plan": {
            "objectifs_couverts": ["Décrire l'intensité du télétravail déclarée."],
            "objectifs_non_couverts": [] if not plan_seulement else [
                "Analyser la relation entre le télétravail et la productivité."],
            "ecarts_methodologie": [],
            "resultats": [] if plan_seulement else [
                {"id_resultat": "R1", "observation": "Le corpus analysé comporte vingt réponses "
                                                     "exploitables.",
                 "objectif": "Décrire l'intensité du télétravail déclarée.", "limites": []}],
            "hypotheses": hypotheses if hypotheses is not None else (
                [] if plan_seulement else [
                    {"hypothese": "L'intensité du télétravail est associée à la productivité "
                                  "déclarée.",
                     "statut": "non_examinable",
                     "justification": "L'effectif est trop faible pour examiner une association.",
                     "resultats": []}]),
            "analyses_realisees": [] if plan_seulement else ["effectifs et fréquences"],
            "analyses_non_realisees": ["test d'association : conditions non réunies"],
            "plan_seulement": plan_seulement,
        },
        "synthese_pour_conclusion": [] if plan_seulement else [
            "Le corpus permet une description, pas une vérification d'association."],
        "interpretation": {"limites_analyse": ["Effectif faible", "Productivité déclarée"]},
        "subject": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "déclarée des développeurs ?",
        "general_objective": "Analyser la relation entre le télétravail et la productivité.",
        "specific_objectives": ["Décrire l'intensité du télétravail déclarée."],
    }


DEFAULT_SYNTHESIS = {
    "elements_disponibles": ["question de recherche", "objectifs", "hypothèses",
                             "méthodologie validée", "résultats vérifiés de l'étape 10"],
    "elements_manquants": ["effectif permettant une analyse relationnelle"],
    "incoherences": [],
    "resultats_essentiels": ["R1", "R2"],
    "reponse_question": {
        "question": "Dans quelle mesure le télétravail influence-t-il la productivité déclarée des "
                    "développeurs ?",
        "reponse": "Le corpus recueilli permet de décrire les réponses obtenues, mais pas d'établir "
                   "une relation entre l'intensité du télétravail et la productivité déclarée.",
        "etayage": ["R1", "R2"],
        "portee": "La réponse reste descriptive : elle ne permet aucune conclusion sur un lien de "
                  "cause à effet, ni aucune généralisation au-delà du corpus étudié.",
    },
    "bilan_objectifs": [
        {"objectif": "Décrire l'intensité du télétravail déclarée.", "statut": "atteint",
         "resultats": ["R1"], "commentaire": "La description est établie sur le corpus recueilli."},
        {"objectif": "Analyser la relation entre le télétravail et la productivité.",
         "statut": "partiellement_atteint", "resultats": ["R2"],
         "commentaire": "Les données ne permettent pas d'examiner la relation."},
    ],
    "bilan_hypotheses": [
        {"hypothese": "L'intensité du télétravail est associée à la productivité déclarée.",
         "statut": "non_examinable",
         "justification": "L'effectif est trop faible pour examiner une association.",
         "resultats": []},
    ],
    "plan_seulement": False,
    "provenance": "provided",
}

DEFAULT_PLAN = {
    "sections": [
        {"titre": "Rappel de l'objectif", "fonction": "situer la conclusion",
         "contenu_prevu": "Rappeler la question et l'objectif du travail.", "retenue": True},
        {"titre": "Synthèse des résultats", "fonction": "rappeler ce qui a été constaté",
         "contenu_prevu": "Présenter les constats du corpus.", "retenue": True},
        {"titre": "Réponse à la question de recherche", "fonction": "répondre explicitement",
         "contenu_prevu": "Énoncer la réponse dans les limites des données.", "retenue": True},
        {"titre": "Limites et perspectives", "fonction": "situer honnêtement le travail",
         "contenu_prevu": "Annoncer les limites et les pistes.", "retenue": True},
    ],
    "rubriques_ecartees": ["Bilan détaillé des hypothèses : données insuffisantes"],
    "adaptation_consignes": "Aucune consigne d'établissement fournie : structure d'usage courant.",
}

DEFAULT_DRAFT = {
    "sections": [
        {"titre": "Rappel de l'objectif",
         "contenu": "Ce travail examine la productivité déclarée des développeurs en télétravail à "
                    "Abidjan, à partir des réponses recueillies par questionnaire.",
         "fonction": "situer la conclusion", "niveau": "constat",
         "justification": "La question et l'objectif du travail sont repris tels quels.",
         "resultats": []},
        {"titre": "Synthèse des résultats",
         "contenu": "Les réponses recueillies ont été décrites : le corpus analysé rassemble vingt "
                    "réponses exploitables et la productivité déclarée peut être résumée.",
         "fonction": "rappeler les constats", "niveau": "constat",
         "justification": "Les constats s'appuient sur les calculs effectués à l'étape des résultats.",
         "resultats": ["R1", "R2"]},
        {"titre": "Réponse à la question de recherche",
         "contenu": "La question posée ne peut recevoir qu'une réponse descriptive avec ce corpus : "
                    "les données recueillies ne permettent pas d'établir une relation entre "
                    "l'intensité du télétravail et la productivité déclarée.",
         "fonction": "répondre explicitement", "niveau": "interpretation",
         "justification": "L'effectif disponible ne permet pas d'examiner une association.",
         "resultats": ["R1", "R2"]},
    ],
    "apports_scientifiques": ["Une description du corpus recueilli sur un terrain peu documenté."],
    "apports_pratiques": [],
    "limites": ["Effectif faible", "Productivité déclarée et non mesurée",
                "Échantillon non probabiliste"],
    "perspectives": ["Étendre le recueil à un effectif permettant d'examiner la relation."],
    "points_a_confirmer": ["Étendue réelle de la population accessible"],
}
