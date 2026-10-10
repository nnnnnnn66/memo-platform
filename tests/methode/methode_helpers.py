"""Aides de test de l'Agent Méthodologie (aucun réseau, aucun coût).

Le module s'appelle `methode_helpers` (jamais `helpers.py`) pour ne pas entrer en collision avec
`tests/helpers.py` quand toute la suite est lancée.

Les fixtures de passation copient la forme RÉELLE des sorties amont (leçon de la chaîne 1 → 8 : les
clés de vérification diffèrent selon l'émetteur, et les champs doivent exister pour de vrai).
"""

import json


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu."""

    def __init__(self, verdict="verified", corrections=None, analysis=None, protocol=None,
                 instruments=None, writing=None):
        self.calls = 0
        self.verdict = verdict
        self.corrections = corrections or []
        self.analysis = analysis or DEFAULT_ANALYSIS
        self.protocol = protocol or DEFAULT_PROTOCOL
        self.instruments = instruments or DEFAULT_INSTRUMENTS
        self.writing = writing or DEFAULT_WRITING
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "methodology_agent", "version": "1.0", "analysis": self.analysis}
        elif "P2 —" in system:
            body = {"agent": "methodology_agent", "version": "1.0", **self.protocol}
        elif "P3 —" in system:
            body = {"agent": "methodology_agent", "version": "1.0", **self.instruments}
        elif "P4 —" in system:
            body = {"agent": "methodology_agent", "version": "1.0", **self.writing}
        elif "Vérificateur" in system:
            body = {"agent": "methodology_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


DEFAULT_ANALYSIS = {
    "discipline": "Sciences de gestion",
    "elements_disponibles": ["diagnostic validé de l'étape 8", "question de recherche",
                             "objectifs de recherche", "accès au terrain confirmé"],
    "elements_manquants": [],
    "contradictions": [],
    "unknowns": [],
    "provenance": "provided",
}

#: Forme RÉELLE de la sortie de l'agent 8 : `verification_result` (et non `validation`).
def upstream_diagnostic(verified=True, status="valide", accepted=True, collecte=None,
                        approche="quantitative", decision="accepted"):
    return {
        "agent": "methodology_diagnostic_agent",
        "version": "1.0",
        "status": "awaiting_human_validation",
        "diagnostic_status": status,
        "provisional": False,
        "subject": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "des développeurs ?",
        "general_objective": "Analyser la relation entre le télétravail et la productivité des "
                             "développeurs.",
        "specific_objectives": ["Identifier les conditions de travail associées à la productivité.",
                                "Examiner l'effet de la coordination des équipes."],
        "diagnosis": {
            "approche": {"code": approche, "proposition": "Approche quantitative",
                         "justification": "La question porte sur une relation mesurable."},
            "logique": {"code": "hypothetico_deductive",
                        "proposition": "Démarche hypothético-déductive",
                        "justification": "Des hypothèses relationnelles sont examinables."},
            "type_recherche": {"code": "explicative", "proposition": "Recherche explicative",
                               "justification": "On cherche à expliquer une relation."},
            "strategie": {"code": "enquete", "proposition": "Enquête par questionnaire",
                          "justification": "Permet de mesurer la relation sur un échantillon."},
            "collecte": collecte if collecte is not None else [
                {"code": "questionnaire", "proposition": "Questionnaire auprès des développeurs"},
            ],
            "analyse": [{"code": "descriptif", "proposition": "Statistiques descriptives"}],
        },
        "verification_result": {"verified": verified,
                                "verifier_status": "verified" if verified else "pending"},
        "student_validation": {"decision": decision if accepted else None, "comment": ""},
    }


DEFAULT_PROTOCOL = {
    "protocol": {
        "approche": "quantitative",
        "logique": "hypothetico_deductive",
        "type_recherche": "explicative",
        "strategie": "enquete",
        "terrain": "Entreprises de services numériques d'Abidjan, 2020-2024.",
        "population": {"cible": "développeurs en télétravail",
                       "accessible": "développeurs de deux entreprises partenaires",
                       "unite_analyse": "le développeur"},
        "echantillonnage": {
            "type": "non_probabiliste",
            "criteres_inclusion": ["exercer en télétravail au moins un jour par semaine"],
            "criteres_exclusion": ["moins de six mois d'ancienneté"],
            "taille": None, "taille_texte": "à déterminer selon les effectifs accessibles",
            "justification": "L'effectif accessible n'est pas encore connu : la taille sera fixée "
                             "après recensement des deux entreprises.",
            "source_taille": "a_determiner", "sans_objet_raison": "",
        },
        "donnees": [{"categorie": "productivité perçue", "description": "auto-évaluation et "
                                                                       "indicateurs de suivi",
                     "origine": "primaire"}],
        "techniques": [{"nom": "questionnaire", "role": "mesurer la relation entre intensité du "
                                                       "télétravail et productivité perçue",
                        "statut": "prevu"}],
        "variables_indicateurs": [{"nom": "intensité du télétravail", "nature": "variable",
                                   "modalites": ["aucun jour", "1-2 jours", "3 jours et plus"]}],
        "analyses": [{"nom": "statistiques descriptives", "objet": "décrire la relation observée",
                      "conditions": [], "statut": "prevu"}],
        "instruments": [],
        "qualite": {"criteres": ["validité de construit", "fiabilité"],
                    "mesures": ["pré-test du questionnaire", "triangulation des sources"]},
        "ethique": {"concerne_personnes": True,
                    "mesures": ["consentement éclairé", "anonymisation des réponses"],
                    "autorisations_necessaires": ["accord des directions des entreprises"],
                    "autorisations_obtenues": "", "autorisations_preuve": ""},
        "limites": [{"description": "échantillon non probabiliste",
                     "consequence": "pas de généralisation statistique"}],
        "etapes": [{"ordre": 1, "intitule": "recenser les effectifs accessibles",
                    "a_confirmer": True}],
        "contradictions_diagnostic": [],
    },
    "elements_a_confirmer": ["effectif accessible dans les deux entreprises"],
}

DEFAULT_INSTRUMENTS = {
    "instruments": [
        {"type": "questionnaire",
         "objet": "mesurer l'intensité du télétravail et la productivité perçue (objectif général)",
         "structure": ["profil", "intensité du télétravail", "productivité perçue",
                       "conditions de travail"],
         "statut": "propose"},
    ],
    "matrice": {
        "lignes": [
            {"objectif": "Analyser la relation entre le télétravail et la productivité des "
                         "développeurs.",
             "donnees_necessaires": ["intensité du télétravail", "productivité perçue"],
             "techniques": ["questionnaire"], "analyses": ["statistiques descriptives"],
             "statut": "couverte", "remarque": ""},
            {"objectif": "Identifier les conditions de travail associées à la productivité.",
             "donnees_necessaires": ["conditions de travail déclarées"], "techniques": ["questionnaire"],
             "analyses": ["tableaux croisés"], "statut": "couverte", "remarque": ""},
            {"objectif": "Examiner l'effet de la coordination des équipes.",
             "donnees_necessaires": ["indicateur de coordination"], "techniques": ["questionnaire"],
             "analyses": ["statistiques descriptives"], "statut": "couverte", "remarque": ""},
        ]
    },
    "elements_a_confirmer": [],
}

DEFAULT_WRITING = {
    "draft": {
        "sections": [
            {"titre": "Approche et type de recherche",
             "contenu": "La recherche s'inscrira dans une approche quantitative, avec une visée "
                        "explicative : il s'agira d'examiner la relation entre l'intensité du "
                        "télétravail et la productivité perçue des développeurs.",
             "statut": "prevu"},
            {"titre": "Population et échantillonnage",
             "contenu": "La population visée est celle des développeurs en télétravail d'Abidjan ; "
                        "la population accessible sera constituée des développeurs de deux "
                        "entreprises partenaires. L'échantillonnage prévu est non probabiliste, par "
                        "volontaires ; la taille sera fixée après recensement des effectifs.",
             "statut": "prevu"},
        ],
        "elements_a_confirmer": ["effectif accessible dans les deux entreprises"],
    }
}
