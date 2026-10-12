"""Orchestrateur de l'étape hypothèses (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → LLM P1 (analyse) → LLM P2 (décision de pertinence)
      → [si HYPOTHESES_RECOMMENDED] LLM P3 (formulation) → contrôles déterministes
      → contrôle de cohérence objectifs↔hypothèses → clarification documentaire (optionnelle)
      → validations → VÉRIFICATEUR indépendant → PORTILLON HUMAIN (décision étudiante).
Une décision HYPOTHESES_NOT_REQUIRED court-circuite P3 : l'agent n'invente jamais d'hypothèses.
Chaque étape est persistée (point de reprise) et bornée. Le statut `validated` n'est jamais posé par
l'agent : il vient de la décision de l'étudiant.
"""

from dataclasses import dataclass, field

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence
from ..schemas.decision import DecisionRequest
from ..schemas.hypotheses import DecisionCode
from ..schemas.output import Evidence, HypothesisStatus, HypothesesOutput
from ..schemas.stages import FormulationOutput
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    alignment_check,
    analysis_stage,
    business_validation,
    clarification_stage,
    decision_stage,
    formulation_stage,
    hypotheses_checks,
    input_controller,
    input_validation,
    pertinence_stage,
    prerequisites,
    security_layer,
    security_validation,
    verifier as verifier_module,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: HypothesesOutput
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


def _confidence(output: HypothesesOutput) -> Confidence:
    """Confiance DÉTERMINÉE par les preuves (jamais auto-attribuée au hasard)."""
    base = 0.5
    decision = output.hypotheses_decision
    if decision == DecisionCode.recommended:
        base += 0.1
    elif decision == DecisionCode.require_clarification:
        base -= 0.2
    verified = 0.15 if output.verification_result.verified else 0.0
    penalty = 0.08 * len(output.ambiguities) + 0.05 * len(output.missing_information)
    overall = round(max(0.0, min(1.0, base + verified - penalty)), 2)
    rationale = (
        f"décision : {decision.value} ; "
        f"vérification indépendante : {'réussie' if output.verification_result.verified else 'non acquise'} ; "
        f"{len(output.ambiguities)} ambiguïté(s), {len(output.missing_information)} information(s) manquante(s)")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, questions: list[str], notes: list[str]) -> HypothesesOutput:
    return HypothesesOutput(
        status=HypothesisStatus.needs_clarification,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        clarification_questions=questions,
        limits_of_this_output=notes,
    )


def _backfill_references(output: HypothesesOutput, request) -> None:
    """Reprend les références DÉJÀ FOURNIES (question, objectifs) — jamais inventées."""
    if not output.main_research_question:
        output.main_research_question = request.effective_question()
    if not output.general_objective:
        output.general_objective = request.effective_general_objective()
    if not output.specific_objectives:
        output.specific_objectives = request.effective_specific_objectives()


def _derived(request, pre, decision_code, formulation) -> tuple[list[str], list[str]]:
    """Champs dérivés (informations manquantes + limites)."""
    missing: list[str] = []
    if not (request.target_population or "").strip():
        missing.append("population cible non précisée")
    if not (request.geographical_area or request.country or "").strip():
        missing.append("zone géographique non précisée")
    if not (request.study_period or "").strip():
        missing.append("période non précisée")
    seen: set[str] = set()
    missing = [m for m in missing if not (m in seen or seen.add(m))]

    limits_notes = list(pre["defaults_used"])
    # Les limites PROPRES aux hypothèses sont des LIMITES, pas des informations manquantes : les mêler
    # à `missing_information` fausse le décompte et brouille le sens (constaté au test réel).
    if decision_code == DecisionCode.recommended:
        for h in formulation.research_hypotheses:
            limits_notes.extend(str(m) for m in h.limits if str(m).strip())
    if decision_code == DecisionCode.recommended and not (request.theoretical_framework or "").strip():
        limits_notes.append(
            "aucun cadre théorique fourni : les justifications des hypothèses reposent sur la "
            "littérature/problématique disponibles seulement — à confirmer avec l'étudiant")
    if missing:
        limits_notes.append(
            "des informations manquantes subsistent avant de figer les hypothèses (voir "
            "missing_information)")
    seen2: set[str] = set()
    limits_notes = [n for n in limits_notes if not (n in seen2 or seen2.add(n))]
    return missing, limits_notes


def _assemble(request, pre, analysis, decision_code, rationale, formulation) -> HypothesesOutput:
    out = HypothesesOutput(
        status=HypothesisStatus.ready_for_verification,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        analysis=analysis,
        hypotheses_decision=decision_code,
        decision_rationale=rationale,
        research_hypotheses=list(formulation.research_hypotheses),
        hypothesis_objective_alignment=formulation.hypothesis_objective_alignment,
        theoretical_or_literature_support=list(formulation.theoretical_or_literature_support),
        required_evidence=list(formulation.required_evidence),
    )
    _backfill_references(out, request)
    out.missing_information, out.limits_of_this_output = _derived(
        request, pre, decision_code, formulation)
    # Une décision RECOMMENDED/NOT_REQUIRED certifie que le travail peut être mené : les points de
    # vigilance de l'analyse sont consignés comme POINTS À CLARIFIER dans les limites, jamais comme
    # `ambiguities` (qui contrediraient la décision) ni comme `clarification_questions` (réservées au
    # chemin needs_clarification). Incohérence signalée deux fois au test réel.
    for text in [str(a).strip() for a in analysis.ambiguites if str(a).strip()]:
        out.limits_of_this_output.append("point à clarifier avec l'étudiant : " + text)
    # Cohérence INTERNE de la sortie : puisque la décision certifie que le travail peut être mené, les
    # points de vigilance ne restent pas dans `analysis.ambiguites` (sinon le dump montre des
    # ambiguïtés bloquantes à côté d'une décision positive — signalé au test réel).
    analysis.ambiguites = []
    out.analysis.ambiguites = []
    return out


def _formulate(llm, request, annotations, analysis, limits, extra: str = "", max_attempts: int = 2):
    """Formule puis applique les contrôles déterministes, avec re-tentative correctrice."""
    attempts = 0
    obj = None
    violations: list[str] = []
    extra_local = extra
    for _ in range(max(1, max_attempts)):
        obj, used = formulation_stage.run(
            llm, request, annotations, analysis, limits, extra=extra_local)
        attempts += used
        provisional = _assemble(request, {"defaults_used": []}, analysis,
                                DecisionCode.recommended, "", obj)
        violations = hypotheses_checks.apply(provisional, request)
        if not violations:
            return obj, attempts, []
        extra_local = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                       + "\n".join(f"- {v}" for v in violations))
    return obj, attempts, violations


def _run_verifier(out: HypothesesOutput, verifier_llm, request, pre, llm, annotations, analysis,
                  settings, result: CampaignResult) -> None:
    """Boucle de vérification avec re-formulation sur corrections. Pose le statut final."""
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = HypothesisStatus.awaiting_human_validation
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = HypothesisStatus.verification_failed
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = HypothesisStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        previous = current
        if out.hypotheses_decision != DecisionCode.recommended:
            # Une décision « pas d'hypothèses » ne se « reformule » pas : les corrections portent sur
            # la justification → on relance la décision de pertinence.
            try:
                code, rationale, questions, used = pertinence_stage.run(
                    llm, request, annotations, analysis, settings.limits,
                    extra="Le vérificateur demande des corrections :\n"
                          + "\n".join(f"- {c}" for c in verdict.corrections))
            except PipelineError:
                out.status = HypothesisStatus.verification_failed
                result.verifier_status = "verification_failed"
                return
            result.attempts += used
            out.hypotheses_decision = code
            out.decision_rationale = rationale
            if code == DecisionCode.require_clarification:
                out.clarification_questions = questions or out.clarification_questions
            result.verifier_status = "corrections_requested"
            result.reformulations += 1
            continue
        extra = ("Le vérificateur demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            formulation, used, violations = _formulate(
                llm, request, annotations, analysis, settings.limits, extra=extra)
        except PipelineError:
            out.status = HypothesisStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        result.attempts += used
        if violations:
            out.status = HypothesisStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.research_hypotheses = list(formulation.research_hypotheses)
        out.hypothesis_objective_alignment = formulation.hypothesis_objective_alignment
        out.theoretical_or_literature_support = list(formulation.theoretical_or_literature_support)
        out.required_evidence = list(formulation.required_evidence)
        out.missing_information, out.limits_of_this_output = _derived(
            request, pre, out.hypotheses_decision, formulation)
        # Confiance RECALCULÉE après reformulation : sinon le vérificateur voit une confiance calculée
        # sur le décompte précédent, incohérente avec `missing_information` (constaté au test réel).
        out.confidence = _confidence(out)
        result.verifier_status = "corrections_requested"
    # La DERNIÈRE reformulation n'était jamais jugée : la boucle sortait sur
    # `verification_failed` alors que la version corrigée peut passer (leçon du test de chaîne
    # réel). Arriver ici signifie qu'une reformulation a bien été produite → on la juge.
    verdict = verifier_module.verify(verifier_llm, request, out)
    result.verifier = verdict
    result.verifications += 1
    if verdict.verdict == VerifierVerdict.verified:
        out.verification_result.verified = True
        out.verification_result.verifier_status = "verified"
        out.status = HypothesisStatus.awaiting_human_validation
        result.verifier_status = "verified"
    else:
        out.status = HypothesisStatus.verification_failed
        result.verifier_status = "verification_failed"


def run(request, settings, llm, verifier_llm=None, allow_network: bool = True, persist=None) -> CampaignResult:
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

    # [1] P1 — analyse de la question et des objectifs
    analysis, a1 = analysis_stage.run(llm, request, annotations, settings.limits)
    stages["analysis"] = {"nature": analysis.nature_du_travail,
                          "provenance": analysis.provenance.value}
    checkpoint("analysis", analysis)

    # [2] P2 — décision de pertinence
    decision_code, rationale, cl_questions, a2 = pertinence_stage.run(
        llm, request, annotations, analysis, settings.limits)
    attempts_total = a1 + a2
    stages["decision"] = {"hypotheses_decision": decision_code.value}

    if decision_code == DecisionCode.require_clarification:
        questions = cl_questions or [a for a in analysis.ambiguites if str(a).strip()]
        if not questions:
            questions = ["Pouvez-vous préciser la question, les objectifs et le cadre théorique "
                         "pour déterminer si des hypothèses sont pertinentes ?"]
        out = _clarification_output(request, questions, pre["defaults_used"])
        out.analysis = analysis
        out.hypotheses_decision = decision_code
        out.decision_rationale = rationale
        checkpoint("hypotheses_output", out)
        return CampaignResult(output=out, attempts=attempts_total, stages=stages,
                              injection_annotations=annotations)

    # [3] P3 — formulation, uniquement si des hypothèses sont recommandées
    if decision_code == DecisionCode.recommended:
        formulation, a3, violations = _formulate(
            llm, request, annotations, analysis, settings.limits)
        attempts_total += a3
        if violations:
            raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                                "hypothèses non conformes : " + " ; ".join(violations[:8]))
        stages["formulation"] = {"count": len(formulation.research_hypotheses)}
    else:
        formulation = FormulationOutput()
        stages["formulation"] = {"count": 0, "note": "HYPOTHESES_NOT_REQUIRED : pas de formulation"}

    out = _assemble(request, pre, analysis, decision_code, rationale, formulation)

    # [4] contrôle de cohérence objectifs ↔ hypothèses (déterministe)
    coherence = alignment_check.check(out.general_objective, out.specific_objectives,
                                      out.research_hypotheses)
    if coherence["uncovered_objectives"]:
        out.hypothesis_objective_alignment.uncovered_objectives = coherence["uncovered_objectives"]
        out.limits_of_this_output.append(
            "objectif(s) non couvert(s) par les hypothèses : "
            + " ; ".join(coherence["uncovered_objectives"]))
    stages["alignment"] = {"uncovered": len(coherence["uncovered_objectives"])}
    checkpoint("hypotheses_proposal", out)

    # [10] clarification documentaire (optionnelle, réseau borné) — sur les ambiguïtés signalées.
    evidence = []
    clarif_stats = {"network_requests": 0, "cache_hits": 0}
    if allow_network:
        terms = [a.description.strip() for a in out.ambiguities if a.description.strip()]
        evidence, clarif_stats, clarif_note = clarification_stage.run(terms, settings)
        stages["clarification"] = {"note": clarif_note, "results": len(evidence)}
    out.source_evidence = evidence

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
        external_requests=clarif_stats["network_requests"],
        cache_hits=clarif_stats["cache_hits"],
        llm_calls=llm.calls,
        stages=stages,
    )

    out.confidence = _confidence(out)

    # [5] VÉRIFICATEUR indépendant
    _run_verifier(out, verifier_llm, request, pre, llm, annotations, analysis, settings, result)

    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme après vérification : " + " ; ".join(post[:8]))

    out.evidence = Evidence(
        llm_calls=llm.calls,
        network_requests=clarif_stats["network_requests"],
        reformulations=result.reformulations,
    )
    out.confidence = _confidence(out)
    result.llm_calls = llm.calls
    checkpoint("hypotheses_output", out)
    return result


def decide(request, settings, llm, output: HypothesesOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant (portillon humain).

    - acceptée (et vérifiée) → `validated`
    - refusée → `blocked`
    - modifiée → la décision de pertinence et/ou les hypothèses de l'étudiant passent les mêmes
      contrôles puis sont re-vérifiées ; `validated` n'arrive qu'après une décision explicite.
    """
    verifier_llm = verifier_llm or llm
    out, needs_revision, violations = decision_stage.apply(output, decision, request)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "hypothèses modifiées non conformes : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_revision and out.status == HypothesisStatus.ready_for_verification:
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = HypothesisStatus.awaiting_human_validation
            result.verifier_status = "verified"
        else:
            out.status = HypothesisStatus.verification_failed
            result.verifier_status = "verification_failed"

    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(post[:8]))
    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=1 if needs_revision else 0)
    out.confidence = _confidence(out)
    return result
