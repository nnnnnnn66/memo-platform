"""Pré-cadrage (SPEC §5) : le travail peut-il commencer sur un cadre suffisant ?

Déterministe. Un prérequis ESSENTIEL manquant arrête la production AVANT tout appel LLM : produire
une problématique non sourcée serait pire que ne rien produire.
"""

ESSENTIAL = {
    "subject_text": "le sujet exact du mémoire",
    "discipline": "la discipline / le champ de recherche",
    "academic_level": "le niveau d'étude (ex. Master 2)",
}

SECONDARY_FIELDS = {
    "population": "la population étudiée",
    "geographical_scope": "la zone géographique étudiée",
    "citation_style": "le style bibliographique demandé",
}


def check(request) -> dict:
    """Retourne {needs_clarification, questions, defaults_used}."""
    missing = [label for field, label in ESSENTIAL.items()
               if not str(getattr(request, field, "") or "").strip()]

    # Le problème concret : soit fourni directement, soit par l'observation de terrain.
    if not (request.research_problem or "").strip() and not (request.field_observations or "").strip():
        missing.append("le problème concret ou l'observation de terrain")

    # La revue de littérature VÉRIFIÉE est la matière première de l'ancrage.
    literature_missing = []
    if request.upstream_literature is None:
        literature_missing.append(
            "la base documentaire de la revue de littérature (étape 3) n'a pas été transmise"
        )
    elif not request.upstream_literature.documents:
        literature_missing.append(
            "la revue de littérature transmise ne contient aucun document"
        )

    questions = [f"Pouvez-vous préciser {label} ?" for label in missing]
    if literature_missing:
        questions.append(
            "Pouvez-vous transmettre la revue de littérature validée (documents + verdict du "
            "vérificateur) ? Sans corpus documentaire vérifié, aucune affirmation ne peut être "
            "sourcée."
        )

    defaults_used = []
    if not request.population:
        defaults_used.append(
            "population non précisée : la cartographie du problème la marquera comme inconnue")
    if not (request.geographical_scope or request.country):
        defaults_used.append("zone géographique non précisée : à confirmer avec l'étudiant")

    return {
        "needs_clarification": bool(missing) or bool(literature_missing),
        "questions": questions,
        "defaults_used": defaults_used,
        "literature_missing": literature_missing,
    }
