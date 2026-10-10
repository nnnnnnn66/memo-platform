"""Application des contrôles déterministes Q1–Q9 et des contrôles de cohérence déclarés."""

from ..analysis import results_rules

_CODE_PREFIXES = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9")


def _strip_code(message: str) -> str:
    text = str(message).strip()
    for code in _CODE_PREFIXES:
        for separator in (f"{code} :", f"{code}:"):
            if text.startswith(separator):
                return text[len(separator):].strip()
    return text


def run(request, computed, plan, interpretation, draft, inventory) -> list[str]:
    return results_rules.run_checks(request, computed, plan, interpretation, draft, inventory)


def coherence_controls(request, computed, plan, interpretation, inventory) -> list[str]:
    """Libellés lisibles (sans code interne) pour la sortie destinée à l'étudiant."""
    controls: list[str] = []
    if not computed.resultats:
        controls.append(
            "aucun calcul n'a pu être réalisé : la production se limite à un plan d'analyse")
    else:
        controls.append(f"{len(computed.resultats)} résultat(s) calculé(s) à partir des données "
                        "réellement fournies")
    non_couverts = [o for o in plan.objectifs_non_couverts if str(o).strip()]
    if non_couverts:
        controls.append("objectifs que les données ne permettent pas de traiter : "
                        + " ; ".join(non_couverts))
    if plan.ecarts_methodologie:
        controls.append("écarts par rapport à la méthodologie validée, à arbitrer : "
                        + " ; ".join(plan.ecarts_methodologie))
    if inventory.manquants:
        controls.append("valeurs manquantes déclarées : " + " ; ".join(inventory.manquants[:5]))
    if inventory.doublons:
        controls.append("doublons déclarés : " + " ; ".join(inventory.doublons[:5]))
    if inventory.anomalies:
        controls.append("anomalies signalées : " + " ; ".join(inventory.anomalies[:5]))
    if inventory.donnees_personnelles:
        controls.append("données personnelles repérées, à anonymiser : "
                        + " ; ".join(inventory.donnees_personnelles[:5]))
    if interpretation.resultats_inattendus:
        controls.append("résultats inattendus présentés : " + " ; ".join(
            interpretation.resultats_inattendus[:5]))
    return controls


def public_messages(violations: list[str]) -> list[str]:
    return [_strip_code(v) for v in violations]
