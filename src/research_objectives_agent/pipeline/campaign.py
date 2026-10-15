"""Orchestrateur de la définition des objectifs de recherche (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → LLM P1 (analyse de la question) → LLM P2 (objectif général)
      → LLM P3 (objectifs spécifiques + alignement + faisabilité) → contrôles déterministes
      → clarification documentaire (optionnelle) → validations
      → VÉRIFICATEUR indépendant → PORTILLON HUMAIN (décision étudiante).
Chaque étape est persistée (point de reprise) et bornée. Le statut `validated` n'est jamais posé par
l'agent : il vient de la décision de l'étudiant.
"""

from dataclasses import dataclass, field

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence
from ..schemas.decision import DecisionRequest
from ..schemas.objectives import Ambiguity
from ..schemas.output import Evidence, ObjectiveStatus, ObjectivesOutput
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    alignment_check,
    analysis_stage,
    business_validation,
    clarification_stage,
    decision_stage,
    general_stage,
    input_controller,
    input_validation,
    objectives_checks,
    prerequisites,
    security_layer,
    security_validation,
    specific_stage,
    verifier as verifier_module,
)

log = get_logger("pipeline.campaign")


# --- Une seule question autorisée : le TERRAIN (consigne du porteur, prioritaire) -------------
# Défaut réel constaté avant démonstration : chaque ambiguïté de l'analyse était transformée en
# question rendue à l'étudiante (« Pouvez-vous préciser : Formulation orientée… »), alors qu'un
# choix de méthode appartient à la plateforme — elle le tranche et le DÉCLARE, l'étudiante pouvant
# corriger en reprenant l'étape.
_MOTS_METHODE = (
    "valider", "décider", "decider", "choisir", "arbitrer", "restreindre", "renoncer",
    "approche", "méthode", "methode", "stratégie", "strategie", "logiciel", "compétence",
    "competence", "critère", "critere", "hypothèse", "hypothese", "formulation", "borne",
    "échelle", "echelle", "échantillon", "echantillon", "indicateur", "variable", "protocole",
)
_MOTS_TERRAIN = (
    "accès", "acces", "autorisation", "joignable", "contact", "disponibilité", "disponibilite",
    "ressource", "budget", "moyen", "terrain", "enquête", "enquete", "document disponible",
    "registre", "donnée disponible", "donnee disponible", "recueillir", "collecte", "délai",
    "delai", "financement", "permis",
)


def _est_question_de_terrain(question: str) -> bool:
    """Une question n'est rendue à l'étudiante que si elle porte sur son TERRAIN."""
    texte = (question or "").lower()
    if any(mot in texte for mot in _MOTS_METHODE):
        return False
    return any(mot in texte for mot in _MOTS_TERRAIN)


@dataclass
class CampaignResult:
    output: ObjectivesOutput
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


def _confidence(output: ObjectivesOutput) -> Confidence:
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


def _clarification_output(request, questions: list[str], notes: list[str]) -> ObjectivesOutput:
    return ObjectivesOutput(
        status=ObjectiveStatus.needs_clarification,
        subject=request.effective_subject(),
        validated_problematic=request.effective_problematic(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        clarification_questions=questions,
        limits_of_this_output=notes,
    )


def _assemble(request, pre, analysis, general, specific) -> ObjectivesOutput:
    """Construit la sortie de proposition à partir des étages, avant vérification."""
    out = ObjectivesOutput(
        status=ObjectiveStatus.ready_for_verification,
        subject=request.effective_subject(),
        validated_problematic=request.effective_problematic(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        question_analysis=analysis,
        general_objective=general,
        specific_objectives=[str(o).strip() for o in specific.specific_objectives
                             if str(o).strip()],
        objective_rationale=specific.objective_rationale,
        question_objective_alignment=specific.question_objective_alignment,
        feasibility_assessment=specific.feasibility_assessment,
    )
    _backfill_scope(out, request)
    # Cohérence des champs : les ambiguïtés relevées à l'analyse remontent au champ de premier niveau,
    # chacune avec sa question de clarification (sinon le vérificateur signale une incohérence —
    # constaté au test réel).
    items = [str(a).strip() for a in analysis.ambiguites if str(a).strip()]
    out.ambiguities = [
        Ambiguity(
            description=text,
            clarification_question=(text if text.endswith("?") else "Pouvez-vous préciser : " + text))
        for text in items
    ]
    out.missing_information, out.limits_of_this_output = _derived(
        request, pre, out.feasibility_assessment, out.scope_and_boundaries)
    # Les ambiguïtés ne sont plus rendues comme des QUESTIONS : elles sont DÉCLARÉES, et seules les
    # questions de terrain restent posées (l'étudiante peut corriger une décision en reprenant
    # l'étape). Défaut réel : six questions de méthode étaient renvoyées pour des choix qui
    # appartiennent à la plateforme.
    out.clarification_questions = [question for question in
                                   (a.clarification_question for a in out.ambiguities)
                                   if _est_question_de_terrain(question)]
    for ambiguite in out.ambiguities:
        if not _est_question_de_terrain(ambiguite.clarification_question):
            out.limits_of_this_output.append(
                "Point tranché par l'agent (à corriger en reprenant l'étape si nécessaire) : "
                + ambiguite.description)
    return out


def _backfill_scope(output: ObjectivesOutput, request) -> None:
    """Complète le périmètre avec les délimitations DÉJÀ FOURNIES (jamais inventées)."""
    scope = output.scope_and_boundaries
    if not (scope.geo or "").strip():
        scope.geo = request.geographical_area or request.country
    if not (scope.temps or "").strip():
        scope.temps = request.study_period
    if not (scope.population or "").strip():
        scope.population = request.target_population


def _derived(request, pre, feasibility, scope):
    """Champs dérivés (informations manquantes + limites) — recalculés après chaque reformulation."""
    missing: list[str] = []
    if not (request.target_population or "").strip():
        missing.append("population cible non précisée")
    if not (request.geographical_area or request.country or "").strip():
        missing.append("zone géographique non précisée")
    if not (request.study_period or "").strip():
        missing.append("période non précisée")
    missing.extend(feasibility.manques)
    seen: set[str] = set()
    missing = [m for m in missing if not (m in seen or seen.add(m))]

    limits_notes = list(pre["defaults_used"])
    if scope.added_without_source:
        limits_notes.append(
            "délimitation (période/zone/population) proposée sans source : à confirmer par l'étudiant")
    # Cohérence des champs : le vérificateur signale un `missing_information` non répercuté dans les
    # limites (constaté au test réel). On répercute explicitement.
    if missing:
        limits_notes.append(
            "des informations manquantes subsistent avant de figer les objectifs (voir "
            "missing_information)")
    if feasibility.verdict.value != "feasible":
        limits_notes.append(
            "faisabilité jugée « " + feasibility.verdict.value + " » au vu des seules informations "
            "fournies : à confirmer avec l'étudiant et son directeur")
    return missing, limits_notes


def _formulate(llm, request, annotations, analysis, limits, extra: str = "", max_attempts: int = 2):
    """Produit objectif général + objectifs spécifiques, avec re-tentative correctrice."""
    attempts = 0
    general = ""
    specific = None
    violations: list[str] = []
    extra_local = extra
    for _ in range(max(1, max_attempts)):
        general, a_g = general_stage.run(
            llm, request, annotations, analysis, limits, extra=extra_local)
        attempts += a_g
        specific, a_s = specific_stage.run(
            llm, request, annotations, analysis, general, limits, extra=extra_local)
        attempts += a_s
        provisional = _assemble(request, {"defaults_used": []}, analysis, general, specific)
        violations = objectives_checks.apply(provisional, request)
        if not violations:
            return general, specific, attempts, []
        extra_local = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                       + "\n".join(f"- {v}" for v in violations))
    return general, specific, attempts, violations


def _run_verifier(out: ObjectivesOutput, verifier_llm, request, question_text, pre, llm,
                  annotations, analysis, settings, result: CampaignResult) -> None:
    """Boucle de vérification avec re-formulation sur corrections. Pose le statut final."""
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out, question_text)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = ObjectiveStatus.awaiting_human_validation
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = ObjectiveStatus.verification_failed
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = ObjectiveStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        previous = current
        extra = ("Le vérificateur demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            general, specific, attempts, violations = _formulate(
                llm, request, annotations, analysis, settings.limits, extra=extra)
        except PipelineError:
            out.status = ObjectiveStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        result.attempts += attempts
        if violations:
            out.status = ObjectiveStatus.verification_failed
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.general_objective = general
        out.specific_objectives = [str(o).strip() for o in specific.specific_objectives
                                   if str(o).strip()]
        out.objective_rationale = specific.objective_rationale
        out.question_objective_alignment = specific.question_objective_alignment
        out.feasibility_assessment = specific.feasibility_assessment
        _backfill_scope(out, request)
        out.missing_information, out.limits_of_this_output = _derived(
            request, pre, out.feasibility_assessment, out.scope_and_boundaries)
        result.verifier_status = "corrections_requested"
    # La DERNIÈRE reformulation n'était jamais jugée : la boucle sortait sur
    # `verification_failed` alors que la version corrigée peut passer (leçon du test de chaîne
    # réel). Arriver ici signifie qu'une reformulation a bien été produite → on la juge.
    verdict = verifier_module.verify(verifier_llm, request, out, question_text)
    result.verifier = verdict
    result.verifications += 1
    if verdict.verdict == VerifierVerdict.verified:
        out.verification_result.verified = True
        out.verification_result.verifier_status = "verified"
        out.status = ObjectiveStatus.awaiting_human_validation
        result.verifier_status = "verified"
    else:
        out.status = ObjectiveStatus.verification_failed
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

    question_text = request.effective_question()
    annotations = security_layer.screen(request, settings.security)

    def checkpoint(name: str, payload) -> None:
        if persist:
            persist(name, payload)

    # [1] P1 — analyse de la question de recherche
    analysis, a1 = analysis_stage.run(llm, request, annotations, settings.limits)
    stages["analysis"] = {"dimensions": len(analysis.dimensions),
                          "provenance": analysis.provenance.value}
    checkpoint("question_analysis", analysis)

    # [2-3] P2 + P3 — objectif général, objectifs spécifiques, alignement, faisabilité
    general, specific, a23, violations = _formulate(
        llm, request, annotations, analysis, settings.limits)
    attempts_total = a1 + a23
    if violations:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "objectifs non conformes : " + " ; ".join(violations[:8]))
    stages["general"] = {"general_objective": general[:160]}
    stages["specific"] = {"count": len(specific.specific_objectives)}

    out = _assemble(request, pre, analysis, general, specific)

    # [4] contrôle de cohérence question ↔ objectifs (déterministe)
    coherence = alignment_check.check(analysis, out.general_objective, out.specific_objectives)
    if coherence["uncovered_dimensions"]:
        out.question_objective_alignment.uncovered_dimensions = coherence["uncovered_dimensions"]
        out.limits_of_this_output.append(
            "dimension(s) de la question non couverte(s) par les objectifs : "
            + " ; ".join(coherence["uncovered_dimensions"]))
    stages["alignment"] = {"uncovered": len(coherence["uncovered_dimensions"])}
    checkpoint("objectives_proposal", out)

    # [10] clarification documentaire (optionnelle, réseau borné) — sur les ambiguïtés signalées.
    evidence = []
    clarif_stats = {"network_requests": 0, "cache_hits": 0}
    if allow_network:
        terms = [a.description.strip() for a in out.ambiguities if a.description.strip()]
        evidence, clarif_stats, clarif_note = clarification_stage.run(terms, settings)
        stages["clarification"] = {"note": clarif_note, "results": len(evidence)}
    out.source_evidence = evidence

    # validations finales
    violations = business_validation.validate_semantics(out, request, question_text)
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

    # [5] VÉRIFICATEUR indépendant → awaiting_human_validation | verification_failed
    _run_verifier(out, verifier_llm, request, question_text, pre, llm, annotations,
                  analysis, settings, result)

    post = business_validation.validate_semantics(out, request, question_text)
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
    checkpoint("objectives_output", out)
    return result


def decide(request, settings, llm, output: ObjectivesOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant (portillon humain).

    - acceptée (et vérifiée) → `validated`
    - refusée → `blocked`
    - modifiée → les objectifs de l'étudiant passent les mêmes contrôles puis sont re-vérifiés.
    """
    verifier_llm = verifier_llm or llm
    question_text = request.effective_question()
    out, needs_revision, violations = decision_stage.apply(output, decision, request)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "objectifs modifiés non conformes : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_revision and out.status == ObjectiveStatus.ready_for_verification:
        verdict = verifier_module.verify(verifier_llm, request, out, question_text)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = ObjectiveStatus.awaiting_human_validation
            result.verifier_status = "verified"
        else:
            out.status = ObjectiveStatus.verification_failed
            result.verifier_status = "verification_failed"

    post = business_validation.validate_semantics(out, request, question_text)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(post[:8]))
    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=1 if needs_revision else 0)
    out.confidence = _confidence(out)
    return result
