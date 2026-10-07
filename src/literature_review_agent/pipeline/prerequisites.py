"""Pré-cadrage (SPEC §5) : vérifie que le travail peut commencer sur un cadre suffisant.

Déterministe. Un prérequis ESSENTIEL manquant arrête la campagne AVANT toute requête réseau :
lancer une collecte documentaire coûteuse hors cadre serait du gaspillage et produirait une revue
inutilisable.
"""

ESSENTIAL = {
    "subject_text": "le sujet exact du mémoire",
    "discipline": "la discipline / le champ de recherche",
    "academic_level": "le niveau d'étude (ex. Master 2)",
}

SECONDARY_FIELDS = {
    "geographical_scope": "la zone géographique étudiée",
    "period": "la période étudiée",
    "citation_style": "le style bibliographique demandé",
}


def check(request) -> dict:
    """Retourne {needs_clarification, questions, defaults_used}."""
    missing = [label for field, label in ESSENTIAL.items()
               if not str(getattr(request, field, "") or "").strip()]
    questions = [f"Pouvez-vous préciser {label} ?" for label in missing]

    defaults_used = []
    if not (request.geographical_scope or request.country):
        defaults_used.append(
            "zone géographique non précisée : recherche mondiale par défaut "
            "(cascade Côte d'Ivoire → Afrique de l'Ouest → Afrique → International)"
        )
    if not request.period:
        defaults_used.append("période non précisée : aucune limite temporelle appliquée")

    # Le style bibliographique a toujours une valeur par défaut déclarée (apa7).
    if not request.citation_style:
        defaults_used.append("style bibliographique non précisé : APA 7 par défaut")

    return {
        "needs_clarification": bool(missing),
        "questions": questions,
        "defaults_used": defaults_used,
    }
