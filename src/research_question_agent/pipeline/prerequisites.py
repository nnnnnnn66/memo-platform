"""Pré-cadrage (SPEC §5, §12) : le travail peut-il commencer sur un cadre suffisant ?

Déterministe. Un prérequis ESSENTIEL manquant arrête la production AVANT tout appel LLM : formuler
une question sans problématique validée serait pire que ne rien produire.
"""

ESSENTIAL = {
    "effective_subject": "le sujet exact du mémoire",
    "discipline": "la discipline / le champ de recherche",
}
SECONDARY_FIELDS = {
    "target_population": "la population étudiée",
    "geographical_area": "la zone géographique étudiée",
    "study_period": "la période étudiée",
}


def check(request) -> dict:
    """Retourne {needs_clarification, questions, defaults_used, problematic_missing}."""
    missing: list[str] = []

    if not request.effective_subject().strip():
        missing.append("le sujet exact du mémoire")
    if not (request.discipline or "").strip():
        missing.append("la discipline / le champ de recherche")

    # La problématique VALIDÉE est le socle de la question de recherche : sans elle, on s'arrête.
    problematic_missing: list[str] = []
    if request.upstream_problematic is not None:
        if not request.upstream_problematic.problematic_line().strip():
            problematic_missing.append(
                "la problématique transmise est vide (aucun texte de problématique exploitable)")
    elif not (request.validated_problematic or "").strip():
        problematic_missing.append(
            "la problématique validée (étape 4) n'a pas été transmise")

    questions = [f"Pouvez-vous préciser {label} ?" for label in missing]
    if problematic_missing:
        questions.append(
            "Pouvez-vous transmettre la problématique validée (texte + verdict du vérificateur) ? "
            "Sans problématique de référence, la question de recherche ne peut pas en découler.")

    defaults_used: list[str] = []
    if not (request.target_population or "").strip():
        defaults_used.append(
            "population non précisée : la compréhension la marquera comme inconnue (jamais inventée)")
    if not (request.geographical_area or request.country or "").strip():
        defaults_used.append("zone géographique non précisée : à confirmer avec l'étudiant")
    if not (request.study_period or "").strip():
        defaults_used.append("période non précisée : à confirmer avec l'étudiant")

    return {
        "needs_clarification": bool(missing) or bool(problematic_missing),
        "questions": questions,
        "defaults_used": defaults_used,
        "problematic_missing": problematic_missing,
    }
