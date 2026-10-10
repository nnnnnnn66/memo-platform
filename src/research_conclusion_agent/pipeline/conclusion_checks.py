"""Application des contrôles déterministes K1–K9 et des contrôles de cohérence déclarés."""

from ..analysis import conclusion_rules

_CODE_PREFIXES = ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9")


def _strip_code(message: str) -> str:
    text = str(message).strip()
    for code in _CODE_PREFIXES:
        for separator in (f"{code} :", f"{code}:"):
            if text.startswith(separator):
                return text[len(separator):].strip()
    return text


def run(request, synthesis, plan, draft) -> list[str]:
    return conclusion_rules.run_checks(request, synthesis, plan, draft)


def coherence_controls(request, synthesis, plan, draft) -> list[str]:
    """Libellés lisibles (sans code interne) pour la sortie destinée à l'étudiant."""
    controls: list[str] = []
    if synthesis.plan_seulement:
        controls.append("aucun résultat vérifié disponible : la production se limite à un plan de "
                        "conclusion")
    else:
        controls.append(f"{len(request.computed_ids())} résultat(s) vérifié(s) disponibles à l'étape 10 ; "
                        f"{len(synthesis.resultats_essentiels)} retenu(s) dans la synthèse")
    if synthesis.bilan_objectifs:
        atteints = [b for b in synthesis.bilan_objectifs
                    if getattr(b.statut, "value", b.statut) == "atteint"]
        controls.append(f"bilan des objectifs : {len(atteints)} atteint(s) sur "
                        f"{len(synthesis.bilan_objectifs)} examiné(s)")
    if synthesis.bilan_hypotheses:
        controls.append(f"hypothèses examinées : {len(synthesis.bilan_hypotheses)}")
    if synthesis.incoherences:
        controls.append("incohérences relevées, à arbitrer : " + " ; ".join(synthesis.incoherences[:4]))
    if draft.limites:
        controls.append("limites annoncées : " + " ; ".join(draft.limites[:4]))
    if draft.perspectives:
        controls.append("perspectives proposées : " + " ; ".join(draft.perspectives[:4]))
    return controls


def public_messages(violations: list[str]) -> list[str]:
    return [_strip_code(v) for v in violations]
