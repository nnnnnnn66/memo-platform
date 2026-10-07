"""Amorce d'alignement méthodologique (SPEC §9.8) — déterministe, matrice en données.

Aucun LLM : la démarche découle du type de gap (matrice `theory/matrix.py`), puis est confrontée au
diagnostic de l'étape 3 (cohérence déclarée, jamais imposée).
"""

from ..schemas.alignment import MethodologicalAlignment, ReasoningLogic, UpstreamCoherence
from ..theory import matrix as theory


def _as_value(value) -> str:
    return getattr(value, "value", str(value))


def build(gap, request, name: str = "") -> MethodologicalAlignment:
    row_id = theory.GAP_TO_MATRIX.get(_as_value(gap.type), "explore_phenomenon")
    row = theory.BY_ID[row_id]

    alignment = MethodologicalAlignment(
        logic=ReasoningLogic(row.reasoning_logic),
        research_type=row.research_type,
        approach=row.approach,
        techniques=list(row.techniques),
        matrix_row_id=row.id,
        justification=(
            f"Le gap retenu est de type « {_as_value(gap.type)} » : {gap.description.strip()[:400]} "
            f"La démarche qui en découle est {row.label.lower()} — logique {row.reasoning_logic}, "
            f"recherche {row.research_type}, approche {row.approach}. "
            "Cette amorce est une PROPOSITION à valider avec l'étudiant et son directeur."
        ),
        alternatives=_alternatives(row),
    )

    upstream = _upstream_diagnosis(request)
    if upstream is None:
        alignment.upstream_coherence = UpstreamCoherence.absent
        alignment.coherence_note = (
            "Aucun diagnostic méthodologique d'amont transmis : l'amorce n'a pas pu être confrontée."
        )
        return alignment

    upstream_logic = theory.normalize_logic(upstream.reasoning_logic or "")
    upstream_approach = _as_value(upstream.approach or "")
    same_logic = upstream_logic == row.reasoning_logic
    compatible_approach = (not upstream_approach) or upstream_approach in {
        row.approach, "mixed_methods"}
    if same_logic and compatible_approach:
        alignment.upstream_coherence = UpstreamCoherence.consistent
        alignment.coherence_note = (
            f"Cohérente avec le diagnostic de l'étape 3 (logique « {upstream_logic} », "
            f"approche « {upstream_approach or 'non précisée'} »)."
        )
    else:
        alignment.upstream_coherence = UpstreamCoherence.divergent
        alignment.coherence_note = (
            f"Divergence déclarée avec le diagnostic de l'étape 3 : celui-ci proposait "
            f"« {upstream_logic} » / « {upstream_approach or 'approche non précisée'} », "
            f"l'amorce déduite du gap propose « {row.reasoning_logic} » / « {row.approach} ». "
            "À arbitrer avec l'étudiant et son directeur."
        )
        alignment.alternatives.append(
            f"Conserver la démarche de l'étape 3 (logique {upstream_logic}, "
            f"approche {upstream_approach or 'non précisée'})"
        )
    return alignment


def _upstream_diagnosis(request):
    if request.upstream_literature is None:
        return None
    diagnosis = request.upstream_literature.diagnosis
    if not (diagnosis.reasoning_logic or diagnosis.approach or diagnosis.matrix_row_id):
        return None
    return diagnosis


def _alternatives(row) -> list[str]:
    others = [r for r in theory.MATRIX if r.id != row.id and r.reasoning_logic != row.reasoning_logic]
    return [f"Si le gap s'avérait {r.label.lower()} : logique {r.reasoning_logic}, "
            f"approche {r.approach}" for r in others[:2]]
