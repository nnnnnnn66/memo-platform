"""Étape [9] — contrôles déterministes de formulation (SPEC §10.C, §10.D, §10.E).

Neutralité, question double, question trop large, délimitation ajoutée sans source. Ces contrôles
sont codés : ils ne dépendent pas de la bonne volonté du modèle.
"""

from ..analysis import question_rules


def check_question_text(question: str, context_text: str) -> list[str]:
    """Contrôles de neutralité/forme sur un texte de question (F2, F3, F4)."""
    violations: list[str] = []
    question = (question or "").strip()
    if not question:
        return ["F1: aucune question fournie"]

    premises = question_rules.detect_premises(question)
    ungrounded = [p for p in premises if not question_rules.premise_is_grounded(p, context_text)]
    if ungrounded:
        violations.append(
            "F2: la question suggère une réponse non établie (présupposé : "
            + ", ".join(sorted(ungrounded)) + "). Reformule-la de façon neutre.")

    if question_rules.is_double_question(question):
        violations.append("F3: la question est double (plusieurs questions en une) : scinde-la "
                          "ou garde une seule question principale")

    if question_rules.is_too_broad(question):
        violations.append("F4: la question est trop générale pour guider une investigation")
    return violations


def apply(formulation, request, problematic_text: str) -> list[str]:
    """Retourne la liste des violations. Marque aussi `scope.added_without_source`."""
    violations: list[str] = []
    context_text = " ".join(filter(None, [
        request.all_provided_text(), problematic_text or "", request.effective_subject()]))

    violations.extend(check_question_text(formulation.main_research_question, context_text))

    # F5 — délimitation ajoutée sans source (doit être déclarée).
    added = question_rules.unsourced_boundaries(formulation.scope_and_boundaries, context_text)
    if added:
        formulation.scope_and_boundaries.added_without_source = True
        violations.append(
            "F5: délimitation ajoutée sans source (" + ", ".join(f"{k}={v}" for k, v in added.items())
            + ") : elle doit être confirmée par l'étudiant, ou retirée")

    # F6 — questions secondaires : utiles, non doubles, non présupposantes.
    for index, secondary in enumerate(formulation.secondary_research_questions, start=1):
        text = (secondary or "").strip()
        if not text:
            violations.append(f"F6: question secondaire {index} vide")
            continue
        for v in check_question_text(text, context_text):
            if v.startswith(("F2", "F3", "F4")):
                violations.append(f"F6: question secondaire {index} — {v.split(': ', 1)[-1]}")
    return violations
