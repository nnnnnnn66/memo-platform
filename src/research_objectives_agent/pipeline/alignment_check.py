"""Étape [4] — contrôle déterministe de la cohérence question ↔ objectifs (SPEC §9.4).

La chaîne « Question → Objectif général → Objectifs spécifiques » doit tenir. Une dimension annoncée
par l'analyse mais non couverte par un objectif spécifique est signalée (jamais inventée).
"""

from ..analysis import objective_rules


def check(analysis, general_objective: str, specifics: list[str]) -> dict:
    """Retourne {issues, uncovered_dimensions}."""
    issues: list[str] = []
    uncovered: list[str] = []

    union = objective_rules.tokens(" ".join([general_objective] + list(specifics)))
    for dimension in analysis.dimensions or []:
        dimension_tokens = objective_rules.tokens(dimension)
        if dimension_tokens and not (dimension_tokens & union):
            uncovered.append(dimension)

    if uncovered:
        issues.append(
            "dimension(s) de la question non couverte(s) par les objectifs : "
            + " ; ".join(uncovered))

    if not objective_rules.tokens(general_objective):
        issues.append("objectif général sans contenu exploitable")

    return {"issues": issues, "uncovered_dimensions": uncovered}
