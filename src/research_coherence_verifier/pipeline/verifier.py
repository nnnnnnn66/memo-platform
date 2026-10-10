"""Contrôleur de l'AUDIT (SPEC §9 étape 5) : l'audit est vérifié avant d'être remis à l'étudiant."""

from pathlib import Path

from ..core.errors import ErrorState, PipelineError
from ..schemas.output import CoherenceOutput
from ..schemas.verifier import VerifierOutput

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "verifier_system.md").read_text(encoding="utf-8")


def _audit_brief(output: CoherenceOutput) -> str:
    lignes = ["<audit_a_controler>", "RAPPORT D'AUDIT À CONTRÔLER :",
              "synthèse : " + output.report.synthese, "",
              f"verdict annoncé : {output.report.verdict.value}",
              f"justification du verdict : {output.report.verdict_justification}", "",
              f"CONSTATS ({len(output.audit.constats)}) :"]
    for constat in output.audit.constats:
        lignes.append(f"- [{constat.code or 'LIBRE'}] ({constat.severite.value}, axe "
                      f"{constat.axe.value}, origine {getattr(constat.origine, 'value', constat.origine)})")
        lignes.append(f"    constat : {constat.constat}")
        lignes.append(f"    preuve  : {constat.preuve}")
        lignes.append(f"    reco.   : {constat.recommandation}")
    if output.audit.constats_infirmes:
        lignes.append("FAITS INFIRMÉS (par l'audit) :")
        for constat in output.audit.constats_infirmes:
            lignes.append(f"- [{constat.code}] {constat.constat} — motif : {constat.motif_suite}")
    lignes.append("")
    lignes.append("PORTÉE DÉCLARÉE (ce que l'audit ne peut PAS vérifier) :")
    for item in output.non_verifiable:
        lignes.append(f"- ({item.portee}) {item.element} — {item.raison}")
    lignes.append("</audit_a_controler>")
    return "\n".join(lignes)


def _dossier_brief(request, output: CoherenceOutput) -> str:
    lignes = ["<elements_du_dossier>", "ÉTAPES DU DOSSIER :"]
    lignes.append("présentes : " + (", ".join(output.etapes_presentes) or "—"))
    lignes.append("absentes : " + (", ".join(output.etapes_absentes) or "aucune"))
    lignes.append("non vérifiées : " + (", ".join(output.etapes_non_verifiees) or "aucune"))
    lignes.append("")
    lignes.append("ÉLÉMENTS DE SERVICE : " + (", ".join(output.elements_de_service) or "—"))
    lignes.append("sujet : " + (request.effective_subject()[:400] or "—"))
    lignes.append("problème : " + (request.effective_problem()[:400] or "—"))
    lignes.append("problématique : " + (request.effective_problematic()[:400] or "—"))
    lignes.append("question : " + (request.effective_question()[:400] or "—"))
    lignes.append("objectif général : " + (request.effective_general_objective()[:400] or "—"))
    for objectif in request.effective_specific_objectives()[:8]:
        lignes.append(f"objectif spécifique : {objectif[:250]}")
    for hypothese in request.effective_hypotheses()[:8]:
        lignes.append(f"hypothèse : {hypothese[:250]}")
    lignes.append("méthodologie : " + (request.methodology_text()[:400] or "—"))
    if request.upstream_results is not None:
        ids = sorted(request.upstream_results.computed_ids())
        lignes.append(f"résultats de l'étape 10 : {len(ids)} calculé(s) — identifiants : "
                      + ", ".join(ids[:40]))
    if request.upstream_conclusion is not None:
        lignes.append("conclusion (réponse) : " + (request.upstream_conclusion.reponse_question()[:600]
                                                   or "—"))
        lignes.append("résultats cités par la conclusion : "
                      + (", ".join(request.upstream_conclusion.references_resultats[:40]) or "aucun"))
    lignes.append("</elements_du_dossier>")
    return "\n".join(lignes)


def verify(llm, request, output: CoherenceOutput) -> VerifierOutput:
    system = load_system()
    user = _audit_brief(output) + "\n\n" + _dossier_brief(request, output)
    from . import llm_stage

    def _checks(obj: VerifierOutput) -> list[str]:
        violations: list[str] = []
        if not obj.controls:
            violations.append("aucun contrôle rendu")
        if obj.verdict.value == "corrections_requested" and not obj.corrections:
            violations.append("verdict « corrections_requested » sans correction listée")
        for correction in obj.corrections:
            if not str(correction).strip():
                violations.append("une correction est vide")
                break
        return violations

    obj, _ = llm_stage.run_json_stage(llm, system, user, VerifierOutput,
                                      extra_checks=_checks, extra="")
    return obj


def ensure_verdict_consistent(output: CoherenceOutput) -> None:
    """Le verdict de l'audit ne peut pas s'écarter de la grille, quoi qu'en dise le contrôleur."""
    from ..schemas.report import verdict_from, verdict_justification

    attendu = verdict_from(output.audit.constats)
    if output.report.verdict != attendu:
        output.report.verdict = attendu
        output.report.verdict_justification = verdict_justification(output.audit.constats, attendu)
        output.corrections_effectuees.append(
            "verdict recalculé par le programme selon la grille imposée")
    if not output.report.verdict_justification.strip():
        output.report.verdict_justification = verdict_justification(output.audit.constats, attendu)


def require_verdict(verdict_value: str) -> None:
    if verdict_value not in ("verified", "corrections_requested", "rejected"):
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, f"verdict inconnu : {verdict_value}")
