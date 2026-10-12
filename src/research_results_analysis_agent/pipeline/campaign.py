"""Orchestrateur de l'Agent Résultats et analyse (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → P1 (inventaire) → MOTEUR DÉTERMINISTE (calculs)
      → P2 (analyse et examen des hypothèses) → P3 (interprétation) → P4 (rédaction + synthèse)
      → contrôles Q1–Q9 + garde numérique → validations S1–S6 → sécurité
      → VÉRIFICATEUR indépendant → PORTILLON HUMAIN.

Les chiffres viennent du CODE : le moteur tourne avant le modèle, qui ne fait que lire et interpréter.
Sans données exploitables, l'agent produit un plan d'analyse — jamais des résultats.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence
from ..schemas.decision import DecisionRequest
from ..schemas.output import DocumentStatus, Evidence, ResultsOutput, ResultsStatus
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    analysis_stage,
    business_validation,
    decision_stage,
    input_controller,
    input_validation,
    interpretation_stage,
    inventory_stage,
    prerequisites,
    results_checks,
    security_layer,
    security_validation,
    verifier as verifier_module,
    writing_stage,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: ResultsOutput
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


def _confidence(output: ResultsOutput) -> Confidence:
    """Confiance DÉTERMINÉE par les preuves, avec la rationale qui ÉNONCE son calcul."""
    base = 0.5
    termes = [f"base {base:.2f}"]
    if not output.computed_results.resultats:
        base -= 0.25
        termes.append("− 0.25 (aucun calcul réalisé : plan d'analyse seulement)")
    if output.document_status in (DocumentStatus.brouillon, DocumentStatus.a_reviser):
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
        f"document {output.document_status.value} ; {len(output.computed_results.resultats)} "
        f"résultat(s) calculé(s) ; vérification indépendante : "
        f"{'réussie' if output.verification_result.verified else 'non acquise'} ; "
        f"calcul : {' '.join(termes)} = {overall:.2f}")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, questions: list[str], notes: list[str]) -> ResultsOutput:
    return ResultsOutput(
        status=ResultsStatus.needs_clarification,
        document_status=DocumentStatus.brouillon,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        questions_for_human=questions,
        informations_a_confirmer=notes,
        limits_of_this_output=notes,
    )


def _assemble(request, inventory, computed, analysis_out, interpretation_out, writing_out):
    trace = f"méthodologie de l'étape 9 : statut « {request.methodology_status() or 'inconnu'} »"
    if request.upstream_methodology is not None and request.upstream_methodology.is_verified:
        trace += " ; vérifiée par son vérificateur"
    trace += (" ; acceptée par l'étudiant" if request.methodology_accepted()
              else " ; décision humaine non consignée dans la transmission")

    out = ResultsOutput(
        status=ResultsStatus.ready_for_verification,
        document_status=DocumentStatus.a_verifier,
        research_id=f"{request.student_id}/{request.session_id or ''}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        version_methodologie_utilisee=request.methodology_status() or "inconnue",
        trace_validation_methodologie=trace,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        hypotheses_examinees=request.effective_hypotheses(),
        inventory=inventory,
        computed_results=computed,
        plan=analysis_out.plan,
        interpretation=interpretation_out.interpretation,
        draft=writing_out.draft,
        synthese_pour_conclusion=list(writing_out.draft.synthese_pour_conclusion),
        transformations_effectuees=list(inventory.manquants) + list(inventory.doublons),
        methodes_et_parametres=[f"{r.methode} — {r.libelle}" for r in computed.resultats[:40]],
    )
    out.origine_des_donnees = [f"{d.nom or 'jeu sans nom'} : {d.source or 'source non précisée'}"
                               for d in request.datasets if str(d.contenu or "").strip()]
    out.origine_des_donnees += [f"{d.reference or 'document sans référence'} : document étudié"
                                for d in request.documents]
    out.periode_et_perimetre = request.data_period or "non précisée"
    out.objectifs_examines = [o for o in [request.effective_general_objective()]
                              + list(request.effective_specific_objectives()) if str(o).strip()]
    out.anomalies_et_manquants = list(inventory.manquants) + list(inventory.anomalies) \
        + list(inventory.doublons)
    out.informations_a_confirmer = list(dict.fromkeys(
        list(writing_out.draft.elements_a_confirmer) + list(interpretation_out.interpretation
                                                            .points_non_resolus)))
    out.sources_externes_consultees = ["aucune recherche externe : analyse des seules données "
                                       "fournies"]
    out.questions_for_human = list(analysis_out.plan.objectifs_non_couverts) \
        + list(analysis_out.plan.ecarts_methodologie)
    out.coherence_controls = results_checks.coherence_controls(
        request, computed, analysis_out.plan, interpretation_out.interpretation, inventory)
    # Les données personnelles repérées IMPLIQUENT une anonymisation : la mesure est DÉCLARÉE
    # par le programme (défaut déterministe corrigé, pas une faute laissée au modèle).
    personnelles = [d for d in inventory.donnees_personnelles
                    if str(d).strip() and not str(d).lower().startswith(("aucun", "pas de", "néant"))]
    if personnelles:
        mesure = ("anonymisation à effectuer avant toute publication : " + " ; ".join(personnelles))
        if mesure not in out.informations_a_confirmer:
            out.informations_a_confirmer.append(mesure)
        if mesure not in out.limits_of_this_output:
            out.limits_of_this_output.append(mesure)
    # Une production qui n'a rien pu calculer est un BROUILLON, jamais un document à valider.
    if not computed.resultats or analysis_out.plan.plan_seulement:
        out.document_status = DocumentStatus.brouillon
        out.plan.plan_seulement = True
        out.limits_of_this_output.append(
            "aucun résultat n'a pu être produit : les données nécessaires ne sont pas disponibles")
    return out


def _derived_missing(request) -> list[str]:
    missing: list[str] = []
    if not request.has_data():
        missing.append("aucune donnée exploitable fournie (résultats impossibles à produire)")
    if not (request.data_origin or "").strip():
        missing.append("origine des données non précisée")
    return missing


def _formulate(llm, request, annotations, inventory, computed, limits, extra: str = "",
               max_attempts: int = 2):
    """Produit P2 → P3 → P4, applique les contrôles déterministes, re-tente si nécessaire."""
    attempts = 0
    out = None
    violations: list[str] = []
    extra_local = extra
    for _ in range(max(1, max_attempts)):
        analysis_out, used2 = analysis_stage.run(
            llm, request, annotations, computed, extra=extra_local)
        attempts += used2
        interpretation_out, used3 = interpretation_stage.run(
            llm, request, annotations, computed, analysis_out.plan, extra=extra_local)
        attempts += used3
        writing_out, used4 = writing_stage.run(
            llm, request, annotations, computed, analysis_out.plan,
            interpretation_out.interpretation, extra=extra_local)
        attempts += used4
        out = _assemble(request, inventory, computed, analysis_out, interpretation_out, writing_out)
        violations = results_checks.run(request, computed, out.plan, out.interpretation,
                                        out.draft, out.inventory)
        if not violations:
            return out, attempts, []
        extra_local = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                       + "\n".join(f"- {v}" for v in violations[:8]))
    return out, attempts, violations


def _run_verifier(out, verifier_llm, request, llm, annotations, inventory, computed, settings,
                  result):
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = ResultsStatus.awaiting_human_validation
            out.document_status = (DocumentStatus.brouillon if out.plan.plan_seulement
                                   else DocumentStatus.en_attente_de_validation)
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = ResultsStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = ResultsStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"
            return
        previous = current
        extra = ("Le vérificateur demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            new_out, used, violations = _formulate(
                llm, request, annotations, inventory, computed, settings.limits, extra=extra)
        except PipelineError:
            out.status = ResultsStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"
            return
        result.attempts += used
        if violations or new_out is None:
            out.status = ResultsStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.plan = new_out.plan
        out.interpretation = new_out.interpretation
        out.draft = new_out.draft
        out.synthese_pour_conclusion = list(new_out.synthese_pour_conclusion)
        out.informations_a_confirmer = list(new_out.informations_a_confirmer)
        out.coherence_controls = results_checks.coherence_controls(
            request, computed, out.plan, out.interpretation, out.inventory)
        out.document_status = (DocumentStatus.brouillon if out.plan.plan_seulement
                               else DocumentStatus.a_verifier)
        out.confidence = _confidence(out)
        result.verifier_status = "corrections_requested"
    # La DERNIÈRE reformulation doit être JUGÉE (leçon du test de chaîne réel).
    verdict = verifier_module.verify(verifier_llm, request, out)
    result.verifier = verdict
    result.verifications += 1
    if verdict.verdict == VerifierVerdict.verified:
        out.verification_result.verified = True
        out.verification_result.verifier_status = "verified"
        out.status = ResultsStatus.awaiting_human_validation
        out.document_status = (DocumentStatus.brouillon if out.plan.plan_seulement
                               else DocumentStatus.en_attente_de_validation)
        result.verifier_status = "verified"
    else:
        out.status = ResultsStatus.verification_failed
        out.document_status = DocumentStatus.a_reviser
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

    # [P1] inventaire et qualité des données
    inventory, a1 = inventory_stage.run(llm, request, annotations)
    stages["inventory"] = {"variables": len(inventory.variables), "lignes": inventory.lignes,
                           "manquants": len(inventory.manquants), "doublons": len(inventory.doublons)}
    checkpoint("inventory", inventory)

    # [MOTEUR] calculs déterministes — AVANT tout appel au modèle
    computed = analysis_stage.compute(request)
    stages["computed"] = {"resultats": len(computed.resultats), "notes": len(computed.notes)}
    checkpoint("computed_results", computed)

    # [P2 → P4] analyse, interprétation, rédaction + contrôles déterministes
    out, a_rest, violations = _formulate(llm, request, annotations, inventory, computed,
                                         settings.limits)
    attempts_total = a1 + a_rest
    if violations or out is None:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "production non conforme : " + " ; ".join(violations[:8]))
    out.missing_information = list(dict.fromkeys(
        out.missing_information + _derived_missing(request)))
    if out.missing_information and not out.computed_results.resultats:
        out.document_status = DocumentStatus.brouillon
    stages["analysis"] = {"resultats": len(out.plan.resultats),
                          "hypotheses": len(out.plan.hypotheses),
                          "plan_seulement": out.plan.plan_seulement}
    checkpoint("results_draft", out)

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

    # VÉRIFICATEUR indépendant
    _run_verifier(out, verifier_llm, request, llm, annotations, inventory, computed, settings,
                  result)

    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme après vérification : " + " ; ".join(post[:8]))

    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=result.reformulations,
                            calculs=len(out.computed_results.resultats))
    out.confidence = _confidence(out)
    result.llm_calls = getattr(llm, "calls", 0)
    checkpoint("results_output", out)
    return result


def decide(request, settings, llm, output: ResultsOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant / de l'encadreur (portillon humain)."""
    verifier_llm = verifier_llm or llm
    out, needs_revision, violations = decision_stage.apply(output, decision, request)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "production modifiée non conforme : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_revision and out.status == ResultsStatus.ready_for_verification:
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = ResultsStatus.awaiting_human_validation
            out.document_status = (DocumentStatus.brouillon if out.plan.plan_seulement
                                   else DocumentStatus.en_attente_de_validation)
            result.verifier_status = "verified"
        else:
            out.status = ResultsStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"

    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=1 if needs_revision else 0,
                            calculs=len(out.computed_results.resultats))
    out.confidence = _confidence(out)
    return result
