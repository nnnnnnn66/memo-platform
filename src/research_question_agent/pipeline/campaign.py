"""Orchestrateur de la formulation de la question de recherche (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → LLM P1 (compréhension) → LLM P2 (intention)
      → contrôle d'intention (déterministe) → LLM P3 (formulation)
      → contrôles de formulation (déterministes) → clarification documentaire (optionnelle)
      → validations → VÉRIFICATEUR indépendant → PORTILLON HUMAIN (décision étudiante).
Chaque étape est persistée (point de reprise) et bornée. Le statut `validated` n'est jamais posé par
l'agent : il vient de la décision de l'étudiant.
"""

from dataclasses import dataclass, field

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence
from ..schemas.output import Evidence, QuestionOutput, QuestionStatus
from ..schemas.decision import DecisionRequest
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    business_validation,
    clarification_stage,
    comprehension_stage,
    decision_stage,
    formulation_checks,
    formulation_stage,
    input_controller,
    input_validation,
    intention_check,
    intention_stage,
    prerequisites,
    security_layer,
    security_validation,
    verifier as verifier_module,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: QuestionOutput
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


def _confidence(output: QuestionOutput) -> Confidence:
    """Confiance DÉTERMINÉE par les preuves (jamais auto-attribuée au hasard)."""
    base = 0.45
    feasibility = output.feasibility_assessment.verdict.value
    bonus = {"feasible": 0.35, "uncertain": 0.15, "not_feasible": 0.0}[feasibility]
    verified = 0.15 if output.verification_result.verified else 0.0
    penalty = 0.08 * len(output.ambiguities) + 0.05 * len(output.missing_information)
    overall = round(max(0.0, min(1.0, base + bonus + verified - penalty)), 2)
    rationale = (
        f"faisabilité : {feasibility} ; "
        f"vérification indépendante : {'réussie' if output.verification_result.verified else 'non acquise'} ; "
        f"{len(output.ambiguities)} ambiguïté(s), {len(output.missing_information)} information(s) manquante(s)")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, questions: list[str], notes: list[str]) -> QuestionOutput:
    return QuestionOutput(
        status=QuestionStatus.needs_clarification,
        subject=request.effective_subject(),
        validated_problematic=request.effective_problematic(),
        clarification_questions=questions,
        limits_of_this_output=notes,
    )


def _formulate(llm, request, annotations, comprehension, intention, limits, problematic,
               extra: str = "", max_attempts: int = 2):
    """Formule puis applique les contrôles déterministes, avec re-tentative correctrice."""
    attempts = 0
    obj = None
    violations: list[str] = []
    for _ in range(max(1, max_attempts)):
        obj, used = formulation_stage.run(
            llm, request, annotations, comprehension, intention, limits,
            extra=extra, student_question=request.research_question_draft)
        attempts += used
        violations = formulation_checks.apply(obj, request, problematic)
        if not violations:
            return obj, attempts, []
        extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                 + "\n".join(f"- {v}" for v in violations))
    return obj, attempts, violations


def _derived(request, pre, feasibility, scope):
    """Champs dérivés (informations manquantes + limites) — recalculés après chaque reformulation.

    Une délimitation n'est DÉCLARÉE MANQUANTE que si elle est vraiment absente des données. Le
    contexte transmis par l'étudiant (sujet, sorties amont) est consulté, comme pour F5 : déclarer
    « population non précisée » alors que l'étudiant l'a fournie dans son sujet est un manque
    FANTOME — il contredit la compréhension et fait refuser l'étape par le vérificateur (défaut
    constaté en répétition générale : la population était dans le sujet, la sortie la déclarait
    pourtant manquante).
    """
    from ..analysis import question_rules

    unsourced = question_rules.unsourced_boundaries(scope, request.all_provided_text())

    def provided(flat_value: str, scope_value: str, field: str) -> bool:
        if (flat_value or "").strip():
            return True
        # La délimitation est fournie si l'agent l'a reprise ET qu'elle est traçable (hors F5).
        return bool((scope_value or "").strip()) and field not in unsourced

    missing: list[str] = []
    if not provided(request.target_population, scope.population, "population"):
        missing.append("population cible non précisée")
    if not provided(request.geographical_area or request.country, scope.geo, "geo"):
        missing.append("zone géographique non précisée")
    if not provided(request.study_period, scope.temps, "temps"):
        missing.append("période non précisée")
    missing.extend(feasibility.manques)
    seen: set[str] = set()
    missing = [m for m in missing if not (m in seen or seen.add(m))]

    limits_notes = list(pre["defaults_used"])
    if scope.added_without_source:
        limits_notes.append(
            "délimitation (zone/période/population) proposée sans source : à confirmer par l'étudiant")
    return missing, limits_notes


def _assemble(request, pre, comprehension, intention, formulation, duplicates=None) -> QuestionOutput:
    """Construit la sortie de proposition à partir des étages, avant vérification."""
    missing_information, limits_notes = _derived(
        request, pre, formulation.feasibility_assessment, formulation.scope_and_boundaries)

    return QuestionOutput(
        status=QuestionStatus.ready_for_verification,
        subject=request.effective_subject(),
        validated_problematic=request.effective_problematic(),
        comprehension=comprehension,
        research_intention=intention,
        main_research_question=formulation.main_research_question,
        secondary_research_questions=list(formulation.secondary_research_questions),
        formulation_rationale=formulation.formulation_rationale,
        scope_and_boundaries=formulation.scope_and_boundaries,
        feasibility_assessment=formulation.feasibility_assessment,
        missing_information=missing_information,
        limits_of_this_output=limits_notes,
    )


def _backfill_scope(output: QuestionOutput, request) -> None:
    """Complète le périmètre avec les délimitations DÉJÀ FOURNIES par l'étudiant (jamais inventées).

    Leçon du test réel : le modèle laisse un champ vide alors que l'information est disponible ;
    on la reprend depuis l'entrée, explicitement écrite — sans inférence.
    """
    scope = output.scope_and_boundaries
    if not (scope.geo or "").strip():
        scope.geo = request.geographical_area or request.country
    if not (scope.temps or "").strip():
        scope.temps = request.study_period
    if not (scope.population or "").strip():
        scope.population = request.target_population


def _run_verifier(out: QuestionOutput, verifier_llm, request, problematic, pre,
                  llm, annotations, comprehension, intention, settings, result: CampaignResult) -> None:
    """Boucle de vérification avec re-formulation sur corrections. Pose le statut final."""
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out, problematic)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = QuestionStatus.awaiting_human_validation
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = QuestionStatus.verification_failed
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = QuestionStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        previous = current
        extra = ("Le vérificateur demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            formulation, attempts, violations = _formulate(
                llm, request, annotations, comprehension, intention, settings.limits, problematic,
                extra=extra)
        except PipelineError:
            out.status = QuestionStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        result.attempts += attempts
        if violations:
            out.status = QuestionStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.main_research_question = formulation.main_research_question
        out.secondary_research_questions = list(formulation.secondary_research_questions)
        out.formulation_rationale = formulation.formulation_rationale
        out.scope_and_boundaries = formulation.scope_and_boundaries
        out.feasibility_assessment = formulation.feasibility_assessment
        # Champs dérivés RAFRAÎCHIS : sans cela, `missing_information` restait celui de la première
        # formulation et pouvait contredire le périmètre corrigé (constaté au test réel).
        _backfill_scope(out, request)
        out.missing_information, out.limits_of_this_output = _derived(
            request, pre, out.feasibility_assessment, out.scope_and_boundaries)
        result.verifier_status = "corrections_requested"
    # La DERNIÈRE reformulation n'était jamais jugée : la boucle sortait sur
    # `verification_failed` alors que la version corrigée peut parfaitement passer (leçon du test de
    # chaîne réel). Arriver ici signifie qu'une reformulation a bien été produite → on la juge.
    verdict = verifier_module.verify(verifier_llm, request, out, problematic)
    result.verifier = verdict
    result.verifications += 1
    if verdict.verdict == VerifierVerdict.verified:
        out.verification_result.verified = True
        out.verification_result.verifier_status = "verified"
        out.status = QuestionStatus.awaiting_human_validation
        result.verifier_status = "verified"
    else:
        out.status = QuestionStatus.verification_failed
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

    problematic = request.effective_problematic()
    annotations = security_layer.screen(request, settings.security)

    def checkpoint(name: str, payload) -> None:
        if persist:
            persist(name, payload)

    # [5] P1 — compréhension de la problématique
    comprehension, a1 = comprehension_stage.run(llm, request, annotations, settings.limits)
    stages["comprehension"] = {"provenance": comprehension.provenance.value}
    checkpoint("comprehension", comprehension)

    # [6] P2 — intention de recherche
    intention, a2 = intention_stage.run(llm, request, annotations, settings.limits)
    stages["intention"] = {"intention": intention.intention}
    checkpoint("intention", intention)

    # [7] contrôle d'intention (déterministe)
    icheck = intention_check.check(intention, comprehension, problematic)
    choix_declare = ""
    if icheck["ambiguous"]:
        # Deux orientations étaient possibles (« mesurer » vs « comprendre »). On ne renvoie plus
        # l'étudiante à sa copie : consigne du porteur, PRIORITAIRE sur la SPEC — un agent TRANCHE
        # et DÉCLARE. Un étudiant qui ne connaît rien à son sujet n'a pas à choisir entre mesurer et
        # comprendre : c'est le travail de la plateforme. On retient l'intention adossée à la
        # problématique validée, on DÉCLARE la lecture écartée, et l'étudiante peut corriger en
        # REPRENANT l'étape (c'est fait pour ça).
        ecartees = [str(a) for a in intention.alternatives if str(a).strip()]
        choix_declare = (
            f"Orientation retenue : « {intention.intention} ». Une autre lecture était possible"
            + (f" ({', '.join(ecartees[:3])})" if ecartees else "")
            + " ; elle aurait conduit à une question différente. La question ci-dessous suit "
              "l'orientation retenue, la mieux adossée à la problématique validée.")
        stages["intention_check"] = {"ambiguous": True, "orientation_retenue": intention.intention}
    if icheck["issues"]:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "intention non conforme : " + " ; ".join(icheck["issues"]))

    # [8-9] P3 — formulation + contrôles déterministes
    formulation, a3, violations = _formulate(
        llm, request, annotations, comprehension, intention, settings.limits, problematic)
    attempts_total = a1 + a2 + a3
    if violations:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "formulation non conforme : " + " ; ".join(violations[:8]))

    # [10] clarification documentaire (optionnelle, réseau borné) — APRÈS assemblage, sur les
    # ambiguïtés réellement signalées (aucune requête si rien à clarifier).
    out = _assemble(request, pre, comprehension, intention, formulation)
    _backfill_scope(out, request)
    if choix_declare:
        out.limits_of_this_output.append(choix_declare)
    evidence = []
    clarif_stats = {"network_requests": 0, "cache_hits": 0}
    if allow_network:
        terms = [a.description.strip() for a in out.ambiguities if a.description.strip()]
        evidence, clarif_stats, clarif_note = clarification_stage.run(terms, settings)
        stages["clarification"] = {"note": clarif_note, "results": len(evidence)}
    out.source_evidence = evidence
    checkpoint("question_proposal", out)

    # [11] validations finales
    violations = business_validation.validate_semantics(out, request, problematic)
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

    # Confiance posée AVANT le vérificateur pour qu'il juge un objet cohérent (sinon il voit 0.0).
    out.confidence = _confidence(out)

    # [12] VÉRIFICATEUR indépendant → awaiting_human_validation | verification_failed
    _run_verifier(out, verifier_llm, request, problematic, pre, llm, annotations,
                  comprehension, intention, settings, result)

    # Re-contrôle final après vérification (statut cohérent)
    post = business_validation.validate_semantics(out, request, problematic)
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
    checkpoint("question_output", out)
    return result


def decide(request, settings, llm, output: QuestionOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant (portillon humain).

    - acceptée (et vérifiée) → `validated`
    - refusée → `blocked`
    - modifiée → la question de l'étudiant passe les mêmes contrôles de neutralité puis est
      re-vérifiée ; elle ne devient `validated` qu'après une décision explicite ultérieure.
    """
    verifier_llm = verifier_llm or llm
    problematic = request.effective_problematic()
    out, needs_revision, violations = decision_stage.apply(output, decision, request, problematic)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "question modifiée non conforme : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_revision and out.status == QuestionStatus.ready_for_verification:
        # Nouvelle vérification de la question modifiée (une passe, sans boucle de re-formulation).
        verdict = verifier_module.verify(verifier_llm, request, out, problematic)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = QuestionStatus.awaiting_human_validation
            result.verifier_status = "verified"
        else:
            out.status = QuestionStatus.verification_failed
            result.verifier_status = "verification_failed"

    post = business_validation.validate_semantics(out, request, problematic)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(post[:8]))
    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0),
                            network_requests=0, reformulations=1 if needs_revision else 0)
    out.confidence = _confidence(out)
    return result
