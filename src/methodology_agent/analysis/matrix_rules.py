"""Construction DÉTERMINISTE de la matrice de cohérence (objectif → données → collecte → analyse).

Le modèle ne décide pas QUELLES lignes existent : une ligne par objectif vérifié de l'étape 6, dans
l'ordre des objectifs. Un objectif absent de la production du modèle devient une ligne
`non_couverte` — il n'est jamais supprimé (règle R4).
"""

import re
import unicodedata

from ..schemas.matrix import CoherenceMatrix, Couverture, MatrixRow


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def _score(a: str, b: str) -> float:
    """Similarité grossière et déterministe entre deux libellés d'objectif."""
    wa, wb = set(_norm(a).split()), set(_norm(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def objectives_of(request) -> list[str]:
    """Les objectifs à couvrir : général puis spécifiques (formes réelles des étapes 6 et 8)."""
    out: list[str] = []
    general = request.effective_general_objective()
    if general:
        out.append(general)
    out.extend(o for o in request.effective_specific_objectives() if str(o).strip())
    return out


def build(request, model_matrix: CoherenceMatrix | None) -> CoherenceMatrix:
    """Reconstruit la matrice en garantissant une ligne par objectif."""
    objectives = objectives_of(request)
    proposed = list(model_matrix.lignes) if model_matrix else []
    rows: list[MatrixRow] = []
    used: set[int] = set()

    for objective in objectives:
        best_index, best_score = None, 0.0
        for index, row in enumerate(proposed):
            if index in used:
                continue
            score = _score(objective, row.objectif)
            if score > best_score:
                best_index, best_score = index, score
        if best_index is not None and best_score >= 0.34:
            used.add(best_index)
            row = proposed[best_index]
            rows.append(MatrixRow(objectif=objective,
                                  donnees_necessaires=list(row.donnees_necessaires),
                                  techniques=list(row.techniques),
                                  analyses=list(row.analyses),
                                  statut=row.statut, remarque=row.remarque))
        else:
            rows.append(MatrixRow(objectif=objective, statut=Couverture.non_couverte,
                                  remarque="Objectif non relié par le protocole : à compléter."))

    # Les lignes proposées pour des objectifs inconnus sont conservées (information, jamais perdue).
    for index, row in enumerate(proposed):
        if index not in used:
            rows.append(row)
    return CoherenceMatrix(lignes=rows)


def recompute_coverage(matrix: CoherenceMatrix) -> CoherenceMatrix:
    """Recalcule le statut de chaque ligne à partir de son contenu (déterministe)."""
    for row in matrix.lignes:
        has_data = bool([d for d in (row.donnees_necessaires or []) if str(d).strip()])
        has_analysis = bool([a for a in (row.analyses or []) if str(a).strip()])
        has_technique = bool([t for t in (row.techniques or []) if str(t).strip()])
        if has_data and has_analysis and has_technique:
            row.statut = Couverture.couverte
        elif has_data or has_analysis or has_technique:
            row.statut = Couverture.partielle
        else:
            row.statut = Couverture.non_couverte
    return matrix


def uncovered(matrix: CoherenceMatrix) -> list[str]:
    return [row.objectif for row in matrix.lignes
            if row.statut != Couverture.couverte and str(row.objectif or "").strip()]


def orphan_objectives(request, matrix: CoherenceMatrix) -> list[str]:
    """Objectifs vérifiés de l'amont absents de la matrice (ne doit jamais arriver)."""
    present = {_norm(row.objectif) for row in matrix.lignes}
    return [o for o in objectives_of(request) if _norm(o) not in present]
