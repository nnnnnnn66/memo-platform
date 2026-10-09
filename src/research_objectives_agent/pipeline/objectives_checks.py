"""Étapes [3-4] — contrôles déterministes des objectifs (SPEC §7, §9.3, §9.4, §10).

Neutralité (aucun résultat présupposé), distinction objectif ≠ hypothèse ≠ activité, non-redondance,
délimitation ajoutée sans source, couverture minimale. Ces contrôles sont CODÉS.
"""

from ..analysis import objective_rules

# Plafond d'alerte (jamais un refus automatique : le nombre dépend du sujet et des consignes).
MAX_SPECIFICS_WARN = 7


def check_general(text: str, context_text: str) -> list[str]:
    """Contrôles O1-O3 sur l'objectif général."""
    violations: list[str] = []
    text = (text or "").strip()
    if not text:
        return ["O1: objectif général absent"]
    if not objective_rules.has_action_verb(text):
        violations.append("O1: l'objectif général ne commence pas par un verbe d'action adapté")
    forbidden = objective_rules.forbidden_verb_hits(text)
    if forbidden:
        violations.append("O2: résultat présupposé par l'objectif (« " + ", ".join(forbidden) + " »)")
    if objective_rules.looks_like_hypothesis(text):
        violations.append("O2: l'objectif général tient lieu d'hypothèse")
    activities = objective_rules.is_activity(text)
    if activities:
        violations.append("O3: l'objectif général décrit une activité, pas une finalité scientifique")
    return violations


def check_specific(text: str, index: int, context_text: str) -> list[str]:
    """Contrôles O4-O6 sur un objectif spécifique."""
    violations: list[str] = []
    text = (text or "").strip()
    if not text:
        return [f"O4: objectif spécifique {index} vide"]
    if not objective_rules.has_action_verb(text):
        violations.append(f"O4: objectif spécifique {index} sans verbe d'action en tête")
    forbidden = objective_rules.forbidden_verb_hits(text)
    if forbidden:
        violations.append(f"O2: objectif spécifique {index} présuppose un résultat ("
                          + ", ".join(forbidden) + ")")
    if objective_rules.looks_like_hypothesis(text):
        violations.append(f"O2: objectif spécifique {index} ressemble à une hypothèse")
    activities = objective_rules.is_activity(text)
    if activities:
        violations.append(f"O3: objectif spécifique {index} décrit une activité, pas un objectif")
    if objective_rules.is_too_short(text, min_tokens=3):
        violations.append(f"O5: objectif spécifique {index} trop vague (trop court)")
    return violations


def apply(output, request) -> list[str]:
    """Contrôles déterministes sur les objectifs assemblés. Marque `scope.added_without_source`."""
    violations: list[str] = []
    context_text = " ".join(filter(None, [
        request.all_provided_text(), request.effective_question(), request.effective_subject()]))

    violations.extend(check_general(output.general_objective, context_text))

    specifics = [str(o).strip() for o in output.specific_objectives]
    for index, text in enumerate(specifics, start=1):
        violations.extend(check_specific(text, index, context_text))

    # O6 — redondance entre objectifs spécifiques.
    for i, j in objective_rules.redundant_pairs(specifics):
        violations.append(f"O6: objectifs spécifiques {i} et {j} se recouvrent (redondance)")

    # O7 — nombre d'objectifs spécifiques (alerte, pas un refus : dépend du sujet).
    if len(specifics) > MAX_SPECIFICS_WARN:
        violations.append(
            f"O7: {len(specifics)} objectifs spécifiques — vérifie qu'aucun n'est superflu "
            "(aucun nombre fixe n'est imposé, mais la complémentarité prime)")

    # O8 — délimitation ajoutée sans source (période/zone/population absente des entrées fournies).
    added = objective_rules.unsourced_boundaries(output.scope_and_boundaries, context_text)
    invented_years = objective_rules.unsourced_years(
        " ".join([output.general_objective] + specifics), context_text)
    if invented_years:
        added["temps"] = ", ".join(invented_years)
    if added:
        output.scope_and_boundaries.added_without_source = True
        violations.append(
            "O8: délimitation ajoutée sans source ("
            + ", ".join(f"{k}={v}" for k, v in added.items())
            + ") : elle doit être confirmée par l'étudiant, ou retirée")

    # O9 — anti-fusion : l'objectif général n'est pas une simple recopie de la question.
    question = (request.effective_question() or "").strip().lower().rstrip("? ")
    general = (output.general_objective or "").strip().lower().rstrip("? ")
    if question and general and question == general:
        violations.append("O9: l'objectif général recopie la question (fusion interdite)")

    return violations
