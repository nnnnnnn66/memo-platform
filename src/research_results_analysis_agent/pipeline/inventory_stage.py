"""Étage P1 — inventaire et qualité des données (SPEC §9 étape 1)."""

from pathlib import Path

from ..analysis import data_engine
from ..schemas.stages import InventoryOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p1_inventory_system.md").read_text(encoding="utf-8")


def deterministic_profile(request) -> str:
    """Profil CALCULÉ des jeux de données, fourni au modèle comme FAIT (jamais à deviner)."""
    lines: list[str] = []
    for index, dataset in enumerate(request.datasets, 1):
        if dataset.format != "csv" or not str(dataset.contenu or "").strip():
            continue
        profil = data_engine.profile(dataset.contenu)
        lines.append(
            f"jeu {index} « {dataset.nom or 'sans nom'} » : {profil['lignes']} lignes, "
            f"{profil['colonnes']} colonnes, {profil['doublons']} doublon(s)")
        for variable in profil["variables"]:
            lines.append(
                f"  - {variable['nom']} ({variable['nature']}), "
                f"{variable['manquants']} valeur(s) manquante(s), "
                f"{len(variable['modalites'])} modalité(s) distincte(s)")
    for index, document in enumerate(request.documents, 1):
        lines.append(f"document {index} « {document.reference or 'sans référence'} » "
                     f"(type {document.type or 'non précisé'}, période "
                     f"{document.periode or 'non précisée'})")
    return "<profil_calcule>\n" + ("\n".join(lines) or "aucune donnée exploitable") + \
        "\n</profil_calcule>"


def _checks(obj: InventoryOutput) -> list[str]:
    violations: list[str] = []
    inventory = obj.inventory
    if not inventory.provenance.strip():
        violations.append("inventory.provenance est vide (d'où viennent les données ?)")
    if not inventory.datasets_resumes and not inventory.analyses_impossibles:
        violations.append("inventory.datasets_resumes est vide (aucun jeu de données décrit)")
    return violations


def run(llm, request, annotations, extra: str = ""):
    system = load_system()
    context = [security_layer.methodology_block(request),
               security_layer.methodology_diff_block(request),
               deterministic_profile(request)]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, InventoryOutput, extra_checks=_checks, extra=extra)
    return obj.inventory, attempts
