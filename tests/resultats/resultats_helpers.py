"""Aides de test de l'Agent Résultats et analyse (aucun réseau, aucun coût).

Les fixtures de passation copient la forme RÉELLE des sorties amont (leçon de la chaîne 1 → 9 : la clé
de vérification diffère selon l'émetteur, et les champs doivent exister pour de vrai).

Les textes de production évitent les nombres non calculés : la garde numérique (Q2) refuse tout chiffre
absent du moteur, y compris dans une fixture de test — c'est précisément ce qu'on veut vérifier.
"""

import json

#: Jeu de données de test : c'est une ENTRÉE (des « données de l'étudiant »), jamais une sortie
#: d'agent. L'agent n'en invente aucune valeur — il la calcule.
CSV = ("id,ville,jours_teletravail,productivite\n"
       "1,Abidjan,3,7\n"
       "2,Abidjan,1,5\n"
       "3,Bouake,0,6\n"
       "4,Abidjan,4,8\n"
       "5,Bouake,,5\n"
       "6,Abidjan,2,6\n")


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu."""

    def __init__(self, verdict="verified", corrections=None, inventory=None, plan=None,
                 interpretation=None, draft=None):
        self.calls = 0
        self.verdict = verdict
        self.corrections = corrections or []
        self.inventory = inventory or DEFAULT_INVENTORY
        self.plan = plan or DEFAULT_PLAN
        self.interpretation = interpretation or DEFAULT_INTERPRETATION
        self.draft = draft or DEFAULT_DRAFT
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "research_results_analysis_agent", "version": "1.0",
                    "inventory": self.inventory}
        elif "P2 —" in system:
            body = {"agent": "research_results_analysis_agent", "version": "1.0",
                    "plan": self.plan}
        elif "P3 —" in system:
            body = {"agent": "research_results_analysis_agent", "version": "1.0",
                    "interpretation": self.interpretation}
        elif "P4 —" in system:
            body = {"agent": "research_results_analysis_agent", "version": "1.0",
                    "draft": self.draft}
        elif "Vérificateur" in system:
            body = {"agent": "results_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


def upstream_methodology(verified=True, status="valide", accepted=True):
    """Forme RÉELLE de la sortie de l'étape 9 (`verification_result`, protocole structuré)."""
    return {
        "agent": "methodology_agent", "version": "1.0",
        "status": "awaiting_human_validation",
        "document_status": status,
        "verification_result": {"verified": verified,
                                "verifier_status": "verified" if verified else "pending"},
        "student_validation": {"decision": "accepted" if accepted else None, "comment": ""},
        "protocol": {
            "approche": "quantitative", "type_recherche": "explicative",
            "strategie": "enquete", "terrain": "Entreprises de services numériques d'Abidjan",
            "techniques": [{"nom": "questionnaire", "role": "mesurer la relation"}],
            "analyses": [{"nom": "statistiques descriptives", "objet": "décrire"}],
            "echantillonnage": {"type": "non_probabiliste", "taille_texte": "six développeurs"},
            "limites": [{"description": "échantillon non probabiliste",
                         "consequence": "pas de généralisation"}],
        },
        "matrice": {"lignes": []},
        "subject": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "déclarée des développeurs ?",
        "general_objective": "Analyser la relation entre le télétravail et la productivité.",
        "specific_objectives": ["Décrire l'intensité du télétravail déclarée."],
    }


DEFAULT_INVENTORY = {
    "datasets_resumes": ["enquete-developpeurs : six réponses de développeurs, questionnaire "
                         "administré en 2024"],
    "variables": [
        {"nom": "ville", "nature": "categorielle", "type_valeurs": "texte", "manquants": 0,
         "transformations": []},
        {"nom": "jours_teletravail", "nature": "numerique", "type_valeurs": "entier",
         "manquants": 1, "transformations": []},
        {"nom": "productivite", "nature": "numerique", "type_valeurs": "entier", "manquants": 0,
         "transformations": []},
    ],
    "lignes": 6, "provenance": "questionnaire administré par l'étudiant", "periode": "2024",
    "manquants": ["jours_teletravail : une réponse manquante sur six"],
    "doublons": [], "anomalies": [],
    "donnees_personnelles": [],
    "analyses_impossibles": ["aucun test statistique inférentiel : effectif trop faible"],
    "provenance_analyse": "provided",
}

DEFAULT_PLAN = {
    "objectifs_couverts": ["Analyser la relation entre le télétravail et la productivité.",
                           "Décrire l'intensité du télétravail déclarée."],
    "objectifs_non_couverts": [],
    "ecarts_methodologie": [],
    "resultats": [
        {"id_resultat": "R1", "observation": "Le fichier comporte six réponses exploitables.",
         "objectif": "Décrire l'intensité du télétravail déclarée.", "limites": []},
    ],
    "hypotheses": [
        {"hypothese": "L'intensité du télétravail est associée à la productivité déclarée.",
         "statut": "non_examinable",
         "justification": "L'effectif est trop faible pour examiner une association : seul un "
                          "descriptif est possible.",
         "resultats": []},
    ],
    "analyses_realisees": ["effectifs et fréquences des modalités de ville",
                           "moyenne et médiane de la productivité déclarée"],
    "analyses_non_realisees": ["test d'association : conditions d'application non réunies"],
    "plan_seulement": False,
}

DEFAULT_INTERPRETATION = {
    "lectures": [
        {"id_resultat": "R1",
         "observation": "Le fichier comporte six réponses exploitables.",
         "objectif": "Décrire l'intensité du télétravail déclarée.",
         "interpretation": "Le corpus reste trop restreint pour dépasser la description : les "
                           "valeurs ne permettent pas de conclure sur une relation.",
         "autres_explications": ["Hétérogénéité des contextes de travail"],
         "limites": ["Effectif très faible", "Productivité déclarée, non mesurée"]},
    ],
    "tableaux": [
        {"titre": "Répartition des répondants par ville",
         "variables": ["ville"], "unites": ["réponses"], "effectif": 6,
         "lecture": "Les répondants se répartissent entre les villes recensées.",
         "resultats": ["R1"]},
    ],
    "figures": [],
    "comparaison_litterature": [],
    "resultats_inattendus": [],
    "limites_analyse": ["Échantillon non probabiliste", "Une réponse manquante"],
    "points_non_resolus": ["Étendue réelle de la population accessible"],
}

DEFAULT_DRAFT = {
    "sections": [
        {"titre": "Présentation des données",
         "contenu": "L'analyse porte sur les réponses recueillies par questionnaire auprès de "
                    "développeurs. Une réponse est manquante pour l'intensité du télétravail.",
         "statut": "etabli", "resultats": ["R1"]},
        {"titre": "Limites de l'analyse",
         "contenu": "L'effectif est faible et la productivité est déclarée, non mesurée : les "
                    "résultats doivent être lus comme descriptifs.",
         "statut": "etabli", "resultats": []},
    ],
    "synthese_pour_conclusion": [
        "Le corpus recueilli permet une description, pas une vérification d'association.",
        "La productivité est déclarée par les répondants, non mesurée."],
    "elements_a_confirmer": ["Étendue de la population accessible"],
}
