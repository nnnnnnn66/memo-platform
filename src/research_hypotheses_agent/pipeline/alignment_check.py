"""Étape [4] — contrôle déterministe de la cohérence objectifs ↔ hypothèses (SPEC §9.4, §10.D).

Une hypothèse qui ne se rattache à aucun objectif est signalée ; un objectif non couvert est déclaré
(jamais inventé).
"""

from ..analysis import hypothesis_rules


def check(general_objective: str, specific_objectives: list[str], hypotheses) -> dict:
    """Retourne {issues, uncovered_objectives}."""
    issues: list[str] = []
    covered = set()
    for h in hypotheses:
        covered |= hypothesis_rules.tokens(
            " ".join([(h.formulation or ""), (h.linked_to or ""), " ".join(h.concepts_variables)]))

    objectives = ([general_objective] if general_objective else []) + list(specific_objectives)
    uncovered: list[str] = []
    for objective in objectives:
        obj_tokens = hypothesis_rules.tokens(objective)
        if obj_tokens and not (obj_tokens & covered):
            uncovered.append(objective)

    if uncovered:
        issues.append("objectif(s) non couvert(s) par les hypothèses : " + " ; ".join(uncovered))

    return {"issues": issues, "uncovered_objectives": uncovered}
