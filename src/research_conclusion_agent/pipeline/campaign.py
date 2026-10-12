"""Orchestrateur de l'Agent Conclusion (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → P1 (examen du dossier et synthèse scientifique)
      → P2 (plan de conclusion) → P3 (rédaction et justifications)
      → contrôles K1–K9 → validations T1–T6 → sécurité
      → VÉRIFICATEUR indépendant → PORTILLON HUMAIN.

Règle structurante : **aucun résultat nouveau**. La conclusion ne synthétise que les résultats vérifiés
de l'étape 10, en les citant par leur identifiant. Sans résultats, elle se limite à un plan.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence
from ..schemas.decision import DecisionRequest
from ..schemas.output import ConclusionOutput, ConclusionStatus, DocumentStatus, Evidence
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    business_validation,
    conclusion_checks,
    decision_stage,
    input_controller,
    input_validation,
    plan_stage,
    prerequisites,
    security_layer,
    security_validation,
    synthesis_stage,
    verifier as verifier_module,
    writing_stage,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: ConclusionOutput
    verifier: VerifierOutput | None = None
    verifier_status: str = "pending"
    attempts: int = 0
    verifications: int = 0
    injection_annotations: list = field(default_factory=list)
    external_requests: int = 0
    cache_hits: int = 0
    llm_calls: int = 0
    reformulations: int = 0
    stages: dict = field(default_factory=dict)


def _confidence(output: ConclusionOutput) -> Confidence:
    """Confiance DÉTERMINÉE par les preuves, avec la rationale qui ÉNONCE son calcul."""
    base = 0.5
    termes = [f"base {base:.2f}"]
    if output.synthesis.plan_seulement:
        base -= 0.25
        termes.append("− 0.25 (aucun résultat vérifié : plan de conclusion seulement)")
    if output.document_status in (DocumentStatus.brouillon, DocumentStatus.a_corriger,
                                  DocumentStatus.a_reviser):
        base -= 0.10
        termes.append("− 0.10 (document de travail, non validé)")
    if output.informations_a_confirmer:
        base -= 0.05
        termes.append(f"− 0.05 ({len(output.informations_a_confirmer)} élément(s) à confirmer)")
    verified = 0.2 if output.verification_result.verified else 0.0
    if verified:
        termes.append("+ 0.20 (vérification indépendante réussie)")
    penalty = 0.05 * len(output.missing_information)
    if penalty:
        termes.append(f"− {penalty:.2f} ({len(output.missing_information)} manque(s) bloquant(s))")
    overall = round(max(0.0, min(1.0, base + verified - penalty)), 2)
    rationale = (
        f"document {output.document_status.value} ; "
        f"{len(output.synthesis.resultats_essentiels)} résultat(s) de l'étape 10 retenu(s) ; "
        f"vérification indépendante : "
        f"{'réussie' if output.verification_result.verified else 'non acquise'} ; "
        f"calcul : {' '.join(termes)} = {overall:.2f}")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, questions: list[str], notes: list[str]) -> ConclusionOutput:
    return ConclusionOutput(
        status=ConclusionStatus.needs_clarification,
        document_status=DocumentStatus.brouillon,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        questions_for_human=questions,
        informations_a_confirmer=notes,
        limits_of_this_output=notes,
    )


def _assemble(request, synthesis, plan, draft) -> ConclusionOutput:
    versions = ["résultats et analyse vérifiés (étape 10)",
                "méthodologie validée (étape 9)"]
    if request.effective_hypotheses():
        versions.append("hypothèses de recherche (étape 7)")
    if (request.university_instructions or "").strip():
        versions.append("consignes de l'établissement (fournies)")
    out = ConclusionOutput(
        status=ConclusionStatus.ready_for_verification,
        document_status=DocumentStatus.brouillon,
        research_id=f"{request.student_id}/{request.session_id or ''}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        version_elements_consultes=versions,
        question_utilisee=request.effective_question(),
        objectifs_utilises=[o for o in [request.effective_general_objective()]
                            + list(request.effective_specific_objectives()) if str(o).strip()],
        references_resultats=list(dict.fromkeys(
            list(synthesis.resultats_essentiels)
            + [r for s in draft.sections for r in (s.resultats or [])])),
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        hypotheses=request.effective_hypotheses(),
        synthesis=synthesis,
        plan=plan,
        draft=draft,
        lacunes_et_incertitudes=list(dict.fromkeys(
            list(synthesis.elements_manquants) + list(draft.points_a_confirmer))),
        incoherences=list(synthesis.incoherences),
        informations_a_confirmer=list(draft.points_a_confirmer),
        coherence_controls=conclusion_checks.coherence_controls(request, synthesis, plan, draft),
    )
    # Sans résultat vérifié, la production est un BROUILLON contenant un plan, jamais une conclusion.
    if synthesis.plan_seulement or not request.available_results():
        out.synthesis.plan_seulement = True
        out.document_status = DocumentStatus.brouillon
        out.draft.sections = []
        if "aucun résultat vérifié disponible : aucune conclusion ne peut être rédigée" \
                not in out.limits_of_this_output:
            out.limits_of_this_output.append(
                "aucun résultat vérifié disponible : aucune conclusion ne peut être rédigée")
    return out


def _derived_missing(request) -> list[str]:
    missing: list[str] = []
    if not request.available_results():
        missing.append("aucun résultat vérifié exploitable (conclusion impossible à fonder)")
    if not request.effective_question().strip():
        missing.append("question de recherche absente")
    return missing


def _formulate(llm, request, annotations, limits, extra: str = "", max_attempts: int = 2):
    """Produit P1 → P2 → P3, applique les contrôles déterministes, re-tente si nécessaire."""
    attempts = 0
    out = None
    violations: list[str] = []
    extra_local = extra
    for _ in range(max(1, max_attempts)):
        synthesis, used1 = synthesis_stage.run(llm, request, annotations, extra=extra_local)
        attempts += used1
        plan_out, used2 = plan_stage.run(llm, request, annotations, synthesis, extra=extra_local)
        attempts += used2
        writing_out, used3 = writing_stage.run(llm, request, annotations, synthesis, plan_out.plan,
                                               extra=extra_local)
        attempts += used3
        out = _assemble(request, synthesis, plan_out.plan, writing_out.draft)
        violations = conclusion_checks.run(request, out.synthesis, out.plan, out.draft)
        if not violations:
            return out, attempts, []
        extra_local = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                       + "\n".join(f"- {v}" for v in violations[:8]))
    return out, attempts, violations


def _run_verifier(out, verifier_llm, request, llm, annotations, settings, result):
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = ConclusionStatus.awaiting_human_validation
            out.document_status = (DocumentStatus.brouillon if out.synthesis.plan_seulement
                                   else DocumentStatus.en_attente_de_validation)
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = ConclusionStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = ConclusionStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"
            return
        previous = current
        extra = ("Le vérificateur demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            new_out, used, violations = _formulate(llm, request, annotations, settings.limits,
                                                   extra=extra)
        except PipelineError:
            out.status = ConclusionStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"
            return
        result.attempts += used
        if violations or new_out is None:
            out.status = ConclusionStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.synthesis = new_out.synthesis
        out.plan = new_out.plan
        out.draft = new_out.draft
        out.informations_a_confirmer = list(new_out.informations_a_confirmer)
        out.lacunes_et_incertitudes = list(new_out.lacunes_et_incertitudes)
        out.references_resultats = list(new_out.references_resultats)
        out.coherence_controls = conclusion_checks.coherence_controls(
            request, out.synthesis, out.plan, out.draft)
        out.document_status = (DocumentStatus.brouillon if out.synthesis.plan_seulement
                               else DocumentStatus.a_corriger)
        out.corrections_effectuees.append(
            "corrections appliquées après vérification : " + " ; ".join(verdict.corrections[:5]))
        out.confidence = _confidence(out)
        result.verifier_status = "corrections_requested"
    # La DERNIÈRE reformulation doit être JUGÉE (leçon du test de chaîne réel).
    verdict = verifier_module.verify(verifier_llm, request, out)
    result.verifier = verdict
    result.verifications += 1
    if verdict.verdict == VerifierVerdict.verified:
        out.verification_result.verified = True
        out.verification_result.verifier_status = "verified"
        out.status = ConclusionStatus.awaiting_human_validation
        out.document_status = (DocumentStatus.brouillon if out.synthesis.plan_seulement
                               else DocumentStatus.en_attente_de_validation)
        result.verifier_status = "verified"
    else:
        out.status = ConclusionStatus.verification_failed
        out.document_status = DocumentStatus.a_corriger
        result.verifier_status = "verification_failed"


def run(request, settings, llm, verifier_llm=None, allow_network: bool = True, persist=None):
    verifier_llm = verifier_llm or llm
    # Remise a zero FACULTATIVE : le contrat d'un client reste `complete()`. Une doublure de
    # test n'a aucun etat a remettre, et lui en imposer un ferait porter au test une obligation
    # qui n'appartient qu'au client reel.
    if hasattr(llm, "nouvelle_campagne"):
        llm.nouvelle_campagne()
    stages: dict = {}

    input_validation.validate(request, settings.limits)
    input_controller.check_upstream(request)

    pre = prerequisites.check(request)
    if pre["needs_clarification"]:
        output = _clarification_output(request, pre["questions"], pre["defaults_used"])
        return CampaignResult(output=output, stages={"prerequisites": pre})

    annotations = security_layer.screen(request, settings.security)

    def checkpoint(name: str, payload) -> None:
        if persist:
            persist(name, payload)

    out, attempts_total, violations = _formulate(llm, request, annotations, settings.limits)
    if violations or out is None:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "conclusion non conforme : " + " ; ".join(violations[:8]))
    out.missing_information = list(dict.fromkeys(
        out.missing_information + _derived_missing(request)))
    stages["synthesis"] = {
        "resultats_retenus": len(out.synthesis.resultats_essentiels),
        "objectifs_examines": len(out.synthesis.bilan_objectifs),
        "hypotheses_examinees": len(out.synthesis.bilan_hypotheses),
        "plan_seulement": out.synthesis.plan_seulement,
    }
    checkpoint("conclusion_draft", out)

    violations = business_validation.validate_semantics(out, request)
    violations += business_validation.validate_final(out)
    if violations:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(violations[:8]))
    security_validation.check_payload(out)

    result = CampaignResult(
        output=out,
        attempts=attempts_total,
        injection_annotations=annotations,
        llm_calls=getattr(llm, "calls", 0),
        stages=stages,
    )
    out.confidence = _confidence(out)

    _run_verifier(out, verifier_llm, request, llm, annotations, settings, result)

    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme après vérification : " + " ; ".join(post[:8]))

    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=result.reformulations,
                            affirmations=len(out.references_resultats))
    out.confidence = _confidence(out)
    result.llm_calls = getattr(llm, "calls", 0)
    checkpoint("conclusion_output", out)
    return result


def decide(request, settings, llm, output: ConclusionOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant / de l'encadreur (portillon humain)."""
    verifier_llm = verifier_llm or llm
    out, needs_revision, violations = decision_stage.apply(output, decision, request)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "conclusion modifiée non conforme : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_revision and out.status == ConclusionStatus.ready_for_verification:
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = ConclusionStatus.awaiting_human_validation
            out.document_status = (DocumentStatus.brouillon if out.synthesis.plan_seulement
                                   else DocumentStatus.en_attente_de_validation)
            result.verifier_status = "verified"
        else:
            out.status = ConclusionStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"

    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=1 if needs_revision else 0,
                            affirmations=len(out.references_resultats))
    out.confidence = _confidence(out)
    return result
