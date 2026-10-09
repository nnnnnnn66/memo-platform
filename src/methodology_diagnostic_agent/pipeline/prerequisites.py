"""Pré-cadrage (SPEC §5, §14) : le diagnostic peut-il être établi ?

Déterministe. Un prérequis ESSENTIEL manquant arrête la production AVANT tout appel LLM : proposer une
méthodologie sans sujet ni question serait pire que ne rien produire.
"""


def check(request) -> dict:
    """Retourne {needs_clarification, questions, defaults_used, subject_missing, question_missing}."""
    missing: list[str] = []

    if not request.effective_subject().strip():
        missing.append("le sujet exact du mémoire")

    question_missing: list[str] = []
    if not request.effective_question().strip():
        question_missing.append("la question de recherche principale")

    questions = [f"Pouvez-vous préciser {label} ?" for label in missing]
    if question_missing:
        questions.append(
            "Pouvez-vous transmettre la question de recherche principale validée (texte + verdict du "
            "vérificateur) ? Sans question de référence, aucun choix méthodologique ne peut être "
            "argumenté.")

    defaults_used: list[str] = []
    if not (request.target_population or "").strip():
        defaults_used.append(
            "population non précisée : la faisabilité et les techniques de collecte restent à confirmer")
    if not (request.geographical_area or request.country or "").strip():
        defaults_used.append("zone géographique non précisée : accès au terrain à confirmer")
    if not (request.available_data or "").strip():
        defaults_used.append("données disponibles non précisées : faisabilité à confirmer")
    if not (request.available_resources or "").strip():
        defaults_used.append("ressources (temps, budget, moyens) non précisées : faisabilité à confirmer")

    return {
        "needs_clarification": bool(missing) or bool(question_missing),
        "questions": questions,
        "defaults_used": defaults_used,
        "subject_missing": missing,
        "question_missing": question_missing,
    }
