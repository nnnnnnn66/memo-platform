"""Étage P1 — audit transversal sémantique (SPEC §9 étape 3).

Le modèle ne refait pas les faits : il JUGE LES LIENS que le programme ne peut pas trancher
(découlement, adéquation, fidélité, fusions reformulées). Il peut confirmer, nuancer ou infirmer chaque
fait — en le motivant.
"""

from pathlib import Path

from ..schemas.stages import AuditOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p1_audit_system.md").read_text(encoding="utf-8")


def _checks(obj: AuditOutput) -> list[str]:
    violations: list[str] = []
    for constat in obj.constats:
        if not str(constat.constat or "").strip():
            violations.append("un constat sans énoncé (champ `constat`)")
            break
        if not str(constat.preuve or "").strip():
            violations.append(f"le constat « {constat.constat[:60]} » est sans PREUVE : un constat "
                              "sans preuve dans le dossier est interdit")
            break
        if not str(constat.recommandation or "").strip():
            violations.append(f"le constat « {constat.constat[:60]} » est sans recommandation")
            break
    if obj.faits_infirmes and not obj.motifs:
        violations.append("des faits sont déclarés infirmés sans motif (`motifs` requis)")
    return violations


def run(llm, request, annotations, dossier_state, faits, extra: str = ""):
    system = load_system()
    context = [
        security_layer.dossier_block(request),
        security_layer.faits_block(faits),
        "ÉTAT DE COMPLÉTUDE : étapes présentes = " + (", ".join(dossier_state.etapes_presentes) or "—")
        + " ; ABSENTES = " + (", ".join(dossier_state.etapes_absentes) or "aucune")
        + " ; NON vérifiées = " + (", ".join(dossier_state.etapes_non_verifiees) or "aucune"),
        "Le dossier est présenté sous forme COMPACTE : chaque coupe est marquée « … » et chaque liste "
        "incomplète est suivie de « … +N autre(s) ». Les listes d'identifiants de résultats "
        "(étape 10 calculés, étape 11 cités) sont EXHAUSTIVES : appuie-toi dessus avant toute "
        "affirmation d'absence. Un faux constat bloque l'audit.",
        "N'INVENTE RIEN. Chaque constat doit citer un élément réellement présent dans le dossier "
        "ci-dessus.",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, AuditOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
