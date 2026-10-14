"""Étages P1 et P2 — analyse du dossier puis protocole détaillé (SPEC §9 étapes 1-2).

P1 : ce que l'agent comprend du dossier (disponible / manquant / contradictoire).
P2 : le protocole opérationnel, construit SUR le diagnostic vérifié de l'étape 8.
"""

from pathlib import Path

from ..schemas.stages import AnalysisOutput, ProtocolOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_p1() -> str:
    return (_PROMPT_DIR / "p1_protocol_system.md").read_text(encoding="utf-8")


def load_p2() -> str:
    return (_PROMPT_DIR / "p2_detailed_system.md").read_text(encoding="utf-8")


def _checks_analysis(obj: AnalysisOutput) -> list[str]:
    violations: list[str] = []
    analysis = obj.analysis
    if not analysis.discipline.strip():
        violations.append("analysis.discipline est vide")
    if not analysis.elements_disponibles:
        violations.append("analysis.elements_disponibles est vide (sur quoi le protocole s'appuie ?)")
    return violations


def run_analysis(llm, request, annotations, extra: str = "", sources_bloc: str = ""):
    system = load_p1()
    # Le diagnostic de l'étape 8 est FOURNI : sans ce bloc, le modèle le déclare « absent du
    # dossier » — contradiction interne relevée par le vérificateur en campagne réelle.
    context = [security_layer.diagnostic_block(request)]
    if sources_bloc:
        context = list(context) + [sources_bloc]
    if sources_bloc:
        context = list(context) + [sources_bloc]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, AnalysisOutput, extra_checks=_checks_analysis, extra=extra)
    return obj.analysis, attempts


def _checks_protocol(obj: ProtocolOutput) -> list[str]:
    violations: list[str] = []
    protocol = obj.protocol
    # Le socle de l'étape 8 est repris, jamais vidé.
    for name in ("approche", "logique", "type_recherche", "strategie"):
        if not str(getattr(protocol, name) or "").strip():
            violations.append(f"protocol.{name} est vide (le socle vérifié de l'étape 8 est repris)")
    if not protocol.terrain.strip():
        violations.append("protocol.terrain est vide (contexte ou terrain d'étude)")
    if not protocol.donnees:
        violations.append("protocol.donnees est vide (données à recueillir)")
    if not protocol.techniques:
        violations.append("protocol.techniques est vide (techniques de collecte)")
    if not protocol.analyses:
        violations.append("protocol.analyses est vide (méthodes de traitement et d'analyse)")
    for entry in protocol.analyses:
        if not str(entry.conditions and "".join(entry.conditions) or "").strip() and \
                any(word in str(entry.nom).lower() for word in ("test", "régression", "corrélation")):
            violations.append(
                f"protocol.analyses « {entry.nom} » : les conditions d'application d'un test "
                "statistique doivent être explicitées")
    return violations


def run_protocol(llm, request, annotations, analysis, extra: str = "", sources_bloc: str = ""):
    system = load_p2()
    context = [
        f"Analyse préalable : disponible = {' ; '.join(analysis.elements_disponibles) or 'aucun'}",
        f"Analyse préalable : manquant (bloquant) = "
        f"{' ; '.join(analysis.elements_manquants) or 'aucun'}",
        f"Analyse préalable : contradictions = {' ; '.join(analysis.contradictions) or 'aucune'}",
        security_layer.diagnostic_block(request),
        ("Objectifs à couvrir :\n"
         + "\n".join(f"- {o}" for o in [request.effective_general_objective()]
                     + list(request.effective_specific_objectives()) if str(o).strip())
         if request.effective_general_objective() or request.effective_specific_objectives() else ""),
        ("Hypothèses à examiner, le cas échéant : " + " ; ".join(request.effective_hypotheses()))
        if request.effective_hypotheses() else "",
    ]
    if sources_bloc:
        context = list(context) + [sources_bloc]
    if sources_bloc:
        context = list(context) + [sources_bloc]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, ProtocolOutput, extra_checks=_checks_protocol, extra=extra)
    return obj, attempts
