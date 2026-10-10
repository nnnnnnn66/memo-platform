"""Aides de test de l'Agent 13 : LLM simulé et dossiers-échantillons.

Les dossiers reproduisent la forme RÉELLE des sorties de la chaîne (clés `verification_result`,
`computed_results.resultats[].id`, `plan.objectifs_non_couverts`, `references_resultats`).
"""

import json

SUJET = "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024"
PROBLEME = ("Les entreprises d'Abidjan ignorent si le télétravail dégrade ou améliore la productivité "
            "de leurs développeurs.")
PROBLEMATIQUE = ("La généralisation du télétravail interroge la manière dont les organisations "
                 "mesurent la performance : la productivité déclarée dépend-elle de l'intensité du "
                 "télétravail, ou d'autres facteurs organisationnels ?")
QUESTION = ("Dans quelle mesure l'intensité du télétravail est-elle associée à la productivité "
            "déclarée des développeurs des entreprises d'Abidjan ?")
OBJECTIF_GENERAL = ("Déterminer si l'intensité du télétravail est associée à la productivité déclarée "
                    "des développeurs.")
OBJECTIFS_SPECIFIQUES = [
    "Décrire l'intensité du télétravail déclarée par les développeurs.",
    "Mesurer la productivité déclarée des développeurs interrogés.",
    "Examiner l'association entre intensité du télétravail et productivité déclarée.",
]
HYPOTHESE = ("L'intensité du télétravail est associée à la productivité déclarée des développeurs.")
CONCLUSION_REPONSE = ("Les données recueillies ne permettent pas d'établir une association entre "
                      "l'intensité du télétravail et la productivité déclarée : la réponse reste "
                      "descriptive.")


def _verifie(**extra):
    base = {"verification_result": {"verified": True, "verifier_status": "verified"}}
    base.update(extra)
    return base


def dossier_complet():
    """Un dossier COMPLET, cohérent, dont tous les liens tiennent."""
    return {
        "student_id": "etu-coherence",
        "session_id": "sess-coherence",
        "discipline": "Sciences de gestion",
        "upstream_subject": {"subject": {"intitule": SUJET}, **_verifie()},
        "upstream_problem": {"identified_problem": {"statement": PROBLEME}, **_verifie()},
        "upstream_literature": {"synthesis": {"references": ["Durand, A. (2019). Télétravail."]},
                                **_verifie()},
        "upstream_problematic": {"validated_problematic": PROBLEMATIQUE, **_verifie()},
        "upstream_question": {"main_research_question": QUESTION, **_verifie()},
        "upstream_objectives": {"general_objective": OBJECTIF_GENERAL,
                                "specific_objectives": OBJECTIFS_SPECIFIQUES, **_verifie()},
        "upstream_hypotheses": {
            "hypotheses_decision": "HYPOTHESES_RECOMMENDED",
            "research_hypotheses": [{"id": "H1", "formulation": HYPOTHESE}], **_verifie()},
        "upstream_methodology_diagnostic": {
            "diagnosis": {"approach": "quantitative",
                          "justification": "Le travail vise à mesurer une association entre deux "
                                           "variables mesurées sur un échantillon."},
            **_verifie()},
        "upstream_methodology": {
            "protocol": {"approche": "quantitative", "type_recherche": "explicative",
                         "strategie": "enquête par questionnaire",
                         "terrain": "entreprises numériques d'Abidjan",
                         "population": "développeurs",
                         "echantillonnage": "échantillon de 120 développeurs"},
            "document_status": "valide", **_verifie()},
        "upstream_results": {
            "computed_results": {"resultats": [
                {"id": "R1", "libelle": "nombre de réponses exploitables", "valeur": "120",
                 "unite": "", "methode": "effectif_total"},
                {"id": "R2", "libelle": "moyenne productivité déclarée", "valeur": "6,15",
                 "unite": "", "methode": "moyenne"},
                {"id": "R3", "libelle": "coefficient d'association télétravail/productivité",
                 "valeur": "0,12", "unite": "", "methode": "corrélation"},
            ]},
            "plan": {"objectifs_couverts": OBJECTIFS_SPECIFIQUES, "objectifs_non_couverts": [],
                     "hypotheses": [{"hypothese": HYPOTHESE, "statut": "soutenue",
                                     "justification": "coefficient faible mais positif",
                                     "resultats": ["R3"]}]},
            "document_status": "valide", **_verifie()},
        "upstream_conclusion": {
            "synthesis": {"reponse_question": {"question": QUESTION, "reponse": CONCLUSION_REPONSE,
                                               "etayage": ["R1", "R2", "R3"]},
                          "bilan_objectifs": [{"objectif": o, "statut": "partiellement_atteint"}
                                              for o in OBJECTIFS_SPECIFIQUES],
                          "bilan_hypotheses": [{"hypothese": HYPOTHESE, "statut": "soutenue",
                                                "justification": "association faible"}]},
            "draft": {"sections": [{"titre": "Réponse", "contenu": CONCLUSION_REPONSE}]},
            "references_resultats": ["R1", "R2", "R3"], "document_status": "valide", **_verifie()},
    }


def dossier_fusionne():
    """Sujet, problème et problématique sont LE MÊME texte : fusion à tort."""
    payload = dossier_complet()
    payload["upstream_problem"] = {"identified_problem": {"statement": SUJET}, **_verifie()}
    payload["upstream_problematic"] = {"validated_problematic": SUJET, **_verifie()}
    return payload


def dossier_objectif_non_couvert():
    payload = dossier_complet()
    plan = dict(payload["upstream_results"]["plan"])
    plan["objectifs_non_couverts"] = [OBJECTIFS_SPECIFIQUES[2]]
    payload["upstream_results"] = {**payload["upstream_results"], "plan": plan}
    return payload


def dossier_reference_orpheline():
    payload = dossier_complet()
    payload["upstream_conclusion"] = {**payload["upstream_conclusion"],
                                      "references_resultats": ["R1", "R2", "R3", "R99"]}
    return payload


def dossier_hypothese_contredite():
    """L'étape 10 juge l'hypothèse non examinable ; la conclusion la dit soutenue."""
    payload = dossier_complet()
    plan = dict(payload["upstream_results"]["plan"])
    plan["hypotheses"] = [{"hypothese": HYPOTHESE, "statut": "non_examinable",
                           "justification": "effectif insuffisant", "resultats": []}]
    payload["upstream_results"] = {**payload["upstream_results"], "plan": plan}
    return payload


def dossier_normatif_non_examinable():
    """Hypothèse relationnelle face à un dispositif purement qualitatif."""
    payload = dossier_complet()
    payload["upstream_methodology"] = {
        "protocol": {"approche": "qualitative", "type_recherche": "descriptive",
                     "strategie": "entretiens semi-directifs", "population": "développeurs"},
        "document_status": "valide", **_verifie()}
    return payload


def dossier_non_verifie():
    """Une étape transmise mais NON vérifiée : l'audit doit le constater, pas le refuser."""
    payload = dossier_complet()
    payload["upstream_objectives"] = {"general_objective": OBJECTIF_GENERAL,
                                      "specific_objectives": OBJECTIFS_SPECIFIQUES,
                                      "verification_result": {"verified": False,
                                                              "verifier_status": "pending"}}
    return payload


def dossier_incomplet():
    """Un dossier réduit : seule la partie finale est transmise."""
    return {"student_id": "etu-partiel", "session_id": "s1",
            "subject_text": SUJET,
            "upstream_results": dossier_complet()["upstream_results"],
            "upstream_conclusion": dossier_complet()["upstream_conclusion"]}


class StubLLM:
    """LLM simulé déterministe : répond selon le prompt système reçu."""

    def __init__(self, constats=None, faits_infirmes=None, motifs=None, synthese=None,
                 recommandations=None, non_verifiable=None, verdict="verified", corrections=None):
        self.calls = 0
        self.constats = constats or []
        self.faits_infirmes = faits_infirmes or []
        self.motifs = motifs or []
        self.synthese = synthese or SYNTHESE
        self.recommandations = recommandations if recommandations is not None else RECOMMANDATIONS
        self.non_verifiable = non_verifiable or []
        self.verdict = verdict
        self.corrections = corrections or []
        self.history = []

    def complete(self, system, user):
        self.calls += 1
        self.history.append(system[:60])
        if "P1 —" in system:
            body = {"agent": "research_coherence_verifier", "version": "1.0",
                    "constats": self.constats, "faits_infirmes": self.faits_infirmes,
                    "motifs": self.motifs, "examens": ["découlement", "service", "fidélité"]}
        elif "P2 —" in system:
            body = {"agent": "research_coherence_verifier", "version": "1.0",
                    "report": {"synthese": self.synthese,
                               "recommandations": self.recommandations},
                    "non_verifiable_supplementaire": self.non_verifiable}
        elif "Contrôleur de l'audit" in system:
            body = {"agent": "coherence_verifier", "version": "1.0", "verdict": self.verdict,
                    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
                    "corrections": list(self.corrections), "flags": []}
        else:
            raise AssertionError("prompt inconnu : " + system[:80])
        return json.dumps(body, ensure_ascii=False)


SYNTHESE = ("Le dossier est solide sur la description du corpus. Une exigence d'association est "
            "annoncée alors que les données recueillies ne permettent pas de l'établir.")
RECOMMANDATIONS = [{"code": "X7", "action": "Déclarer l'association non examinable dans la conclusion.",
                    "vers_etape": "hypotheses"}]
