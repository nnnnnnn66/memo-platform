"""Application des contrôles déterministes P1–P9 et des contrôles de cohérence déclarés.

Ces contrôles ne remplacent pas le vérificateur : ils l'ALIMENTENT et empêchent qu'une production
manifestement non conforme lui soit transmise.
"""

from ..analysis import matrix_rules, protocol_rules

#: Préfixes de code à ne JAMAIS exposer à l'étudiant (les codes restent dans les violations et les
#: journaux — leçon de l'étape 8 : « M1–M3 : contrôle déterministe » a été jugé illisible).
_CODE_PREFIXES = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9")


def _strip_code(message: str) -> str:
    text = str(message).strip()
    for code in _CODE_PREFIXES:
        if text.startswith(f"{code} :"):
            return text[len(code) + 2:].strip()
        if text.startswith(f"{code}:"):
            return text[len(code) + 1:].strip()
    return text


def run(request, protocol, matrix, draft, analysis) -> list[str]:
    """Retourne les violations (vide = conforme)."""
    return protocol_rules.run_checks(request, protocol, matrix, draft, analysis)


def coherence_controls(request, protocol, matrix) -> list[str]:
    """Libellés lisibles (sans code interne) pour la sortie destinée à l'étudiant."""
    controls: list[str] = []
    uncovered = matrix_rules.uncovered(matrix)
    if uncovered:
        controls.append(
            "objectifs non entièrement couverts par le protocole : " + " ; ".join(uncovered))
    orphans = matrix_rules.orphan_objectives(request, matrix)
    for objective in orphans:
        controls.append(f"objectif sans ligne de matrice (à compléter) : {objective}")
    if protocol.contradictions_diagnostic:
        controls.append(
            "contradictions avec le diagnostic vérifié, à arbitrer : "
            + " ; ".join(protocol.contradictions_diagnostic))
    if protocol.echantillonnage.type.value == "sans_objet":
        controls.append(
            "aucune population de personnes n'est échantillonnée : "
            + (protocol.echantillonnage.sans_objet_raison or "raison à préciser"))
    return controls


def public_messages(violations: list[str]) -> list[str]:
    """Version sans codes internes, destinée au rapport étudiant."""
    return [_strip_code(v) for v in violations]
