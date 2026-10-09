"""Pré-cadrage (SPEC §5, §12) : les objectifs peuvent-ils être définis sur un cadre suffisant ?

Déterministe. Un prérequis ESSENTIEL manquant arrête la production AVANT tout appel LLM : définir des
objectifs sans question de recherche validée serait pire que ne rien produire.
"""

ESSENTIAL = {}


def check(request) -> dict:
    """Retourne {needs_clarification, questions, defaults_used, question_missing}."""
    missing: list[str] = []

    if not request.effective_subject().strip():
        missing.append("le sujet exact du mémoire")
    if not (request.discipline or "").strip():
        missing.append("la discipline / le champ de recherche")

    # La question de recherche VALIDÉE est le socle des objectifs : sans elle, on s'arrête.
    question_missing: list[str] = []
    if not request.effective_question().strip():
        question_missing.append(
            "la question de recherche validée (étape 5) n'a pas été transmise")

    questions = [f"Pouvez-vous préciser {label} ?" for label in missing]
    if question_missing:
        questions.append(
            "Pouvez-vous transmettre la question de recherche principale validée (texte + verdict "
            "du vérificateur) ? Sans question de référence, les objectifs ne peuvent pas en découler.")

    defaults_used: list[str] = []
    if not (request.target_population or "").strip():
        defaults_used.append(
            "population non précisée : l'analyse la marquera comme inconnue (jamais inventée)")
    if not (request.geographical_area or request.country or "").strip():
        defaults_used.append("zone géographique non précisée : à confirmer avec l'étudiant")
    if not (request.study_period or "").strip():
        defaults_used.append("période non précisée : à confirmer avec l'étudiant")

    return {
        "needs_clarification": bool(missing) or bool(question_missing),
        "questions": questions,
        "defaults_used": defaults_used,
        "question_missing": question_missing,
    }
