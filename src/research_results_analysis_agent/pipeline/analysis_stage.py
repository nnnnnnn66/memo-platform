"""Étage P2 — moteur de calcul puis plan d'analyse et lecture des résultats (SPEC §9 étapes 2-3).

Le moteur DÉTERMINISTE tourne AVANT le modèle : les valeurs calculées sont passées comme FAITS. Le
modèle ne calcule jamais — il lit, relie aux objectifs et examine les hypothèses.
"""

from pathlib import Path

from ..analysis import data_engine
from ..schemas.analysis import ComputedResults
from ..schemas.stages import AnalysisOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p2_analysis_system.md").read_text(encoding="utf-8")


def compute(request) -> ComputedResults:
    """Exécute le moteur déterministe sur tout ce qui a été réellement fourni."""
    resultats: list[dict] = []
    notes: list[str] = []
    for dataset in request.datasets:
        if dataset.format != "csv":
            notes.append(f"jeu « {dataset.nom or 'sans nom'} » non tabulaire : non calculé, traité "
                         "comme notes")
            continue
        if not str(dataset.contenu or "").strip():
            notes.append(f"jeu « {dataset.nom or 'sans nom'} » vide : aucun calcul possible")
            continue
        resultats.extend(data_engine.compute(dataset.contenu, dataset.nom or ""))
    if request.documents:
        resultats.extend(data_engine.compute_documents(list(request.documents)))
    return ComputedResults.model_validate({"resultats": resultats, "notes": notes})


def computed_block(computed: ComputedResults) -> str:
    """Les résultats CALCULÉS, présentés au modèle comme les seuls faits chiffrés disponibles."""
    lines = ["<resultats_calcules>",
             "RÉSULTATS CALCULÉS PAR LE PROGRAMME — ce sont les SEULS chiffres que tu peux citer. "
             "Chaque affirmation chiffrée doit référencer l'identifiant (R…) ; tu ne dois JAMAIS "
             "produire un chiffre qui ne figure pas ici."]
    for resultat in computed.resultats:
        lines.append(
            f"- {resultat.id} : {resultat.libelle} = {resultat.valeur}{(' ' + resultat.unite) if resultat.unite else ''}"
            f" (effectif {resultat.effectif} ; méthode {resultat.methode})")
    for note in computed.notes:
        lines.append(f"- note : {note}")
    if not computed.resultats:
        lines.append("- AUCUN calcul possible : aucune donnée tabulaire exploitable n'a été fournie.")
    lines.append("</resultats_calcules>")
    return "\n".join(lines)


def _checks(obj: AnalysisOutput) -> list[str]:
    violations: list[str] = []
    plan = obj.plan
    if not plan.resultats and not plan.plan_seulement:
        violations.append(
            "plan.resultats est vide sans que `plan_seulement` soit vrai : soit des résultats "
            "calculés sont interprétés, soit la production se déclare plan d'analyse seulement")
    for resultat in plan.resultats:
        if not str(resultat.id_resultat or "").strip():
            violations.append("un résultat est affirmé sans référence à un calcul (`id_resultat`)")
            break
    if not plan.analyses_realisees and not plan.plan_seulement:
        violations.append("plan.analyses_realisees est vide (qu'est-ce qui a réellement été calculé ?)")
    return violations


def run(llm, request, annotations, computed: ComputedResults, extra: str = ""):
    system = load_system()
    context = [security_layer.methodology_block(request), computed_block(computed),
               security_layer.methodology_diff_block(request)]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, AnalysisOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
