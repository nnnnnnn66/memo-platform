"""Orchestrateur de l'Agent Méthodologie (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → P1 (analyse du dossier) → P2 (protocole détaillé)
      → P3 (instruments + matrice de cohérence) → P4 (rédaction de la section)
      → contrôles déterministes P1–P9 → validations (R1–R6) → sécurité
      → VÉRIFICATEUR indépendant → PORTILLON HUMAIN (décision étudiante / encadreur).

Le protocole reste un DOCUMENT DE TRAVAIL tant que la décision humaine n'est pas rendue : le statut
`validated` n'est jamais posé par l'agent.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..analysis import matrix_rules
from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence
from ..schemas.decision import DecisionRequest
from ..schemas.output import DocumentStatus, Evidence, MethodologyOutput, MethodologyStatus
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    business_validation,
    decision_stage,
    input_controller,
    input_validation,
    instruments_stage,
    prerequisites,
    protocol_checks,
    protocol_stage,
    research_stage,
    security_layer,
    security_validation,
    verifier as verifier_module,
    writing_stage,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: MethodologyOutput
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


def _confidence(output: MethodologyOutput) -> Confidence:
    """Confiance DÉTERMINÉE par les preuves, avec la rationale qui ÉNONCE son calcul."""
    base = 0.5
    termes = [f"base {base:.2f}"]
    if output.document_status in (DocumentStatus.brouillon, DocumentStatus.a_reviser):
        base -= 0.15
        termes.append("− 0.15 (document de travail, non validé)")
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
    inconnues = f", {len(output.unknowns)} inconnue(s) déclarée(s)" if output.unknowns else ""
    rationale = (
        f"document {output.document_status.value} ; vérification indépendante : "
        f"{'réussie' if output.verification_result.verified else 'non acquise'} ; "
        f"{len(output.informations_a_confirmer)} élément(s) à confirmer, "
        f"{len(output.missing_information)} information(s) manquante(s){inconnues} ; "
        f"calcul : {' '.join(termes)} = {overall:.2f}")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, questions: list[str], notes: list[str]) -> MethodologyOutput:
    return MethodologyOutput(
        status=MethodologyStatus.needs_clarification,
        document_status=DocumentStatus.brouillon,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        questions_for_human=questions,
        informations_a_confirmer=notes,
        limits_of_this_output=notes,
    )


def _diagnostic_present(request) -> bool:
    payload = request.upstream_methodology_diagnostic
    return payload is not None and bool(request.diagnostic_categories())


def _clean_missing(request, items) -> list[str]:
    """Retire les manques qui CONTREDISENT un élément pourtant fourni.

    Défaut déterministe constaté en campagne réelle : le modèle déclarait le « diagnostic de l'étape
    8 absent du dossier » alors qu'il le lisait, produisant une contradiction interne que le
    vérificateur a relevée (C13). Un manque qui nie un élément présent est retiré, pas discuté.
    """
    out: list[str] = []
    for item in items or []:
        text = str(item).strip()
        if not text:
            continue
        lowered = text.lower()
        about_diagnostic = "diagnostic" in lowered and ("etape 8" in lowered or "étape 8" in lowered)
        if about_diagnostic and _diagnostic_present(request):
            continue
        if text not in out:
            out.append(text)
    return out


def _assemble(request, analysis, protocol_out, instruments_out, writing_out,
              recherche=None) -> MethodologyOutput:
    protocol = protocol_out.protocol
    matrix = matrix_rules.recompute_coverage(
        matrix_rules.build(request, instruments_out.matrice))
    # Les instruments produits à l'étape P3 sont versés au protocole (une seule source de vérité).
    if not protocol.instruments:
        protocol.instruments = list(instruments_out.instruments)

    hypotheses = request.effective_hypotheses()
    # La trace de validation est DÉRIVÉE des faits transmis, jamais affirmée en bloc.
    trace = f"diagnostic de l'étape 8 : statut « {request.diagnostic_status() or 'inconnu'} »"
    if request.upstream_methodology_diagnostic is not None \
            and request.upstream_methodology_diagnostic.is_verified:
        trace += " ; vérifié par son vérificateur"
    trace += (" ; accepté par l'étudiant" if request.diagnostic_accepted()
              else " ; décision humaine non consignée dans la transmission")
    out = MethodologyOutput(
        status=MethodologyStatus.ready_for_verification,
        document_status=DocumentStatus.a_verifier,
        research_id=f"{request.student_id}/{request.session_id or ''}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        version_diagnostic_utilisee=request.diagnostic_status() or "inconnue",
        trace_validation_diagnostic=trace,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        hypotheses_examined=hypotheses,
        analysis=analysis,
        protocol=protocol,
        matrice=matrix,
        draft=writing_out.draft,
        informations_a_confirmer=list(dict.fromkeys(
            list(protocol_out.elements_a_confirmer)
            + list(instruments_out.elements_a_confirmer)
            + list(writing_out.draft.elements_a_confirmer))),
    )
    choix = [f"approche : {protocol.approche}", f"logique : {protocol.logique}",
             f"type de recherche : {protocol.type_recherche}", f"stratégie : {protocol.strategie}"]
    out.choix_methodologiques_retenus = [c for c in choix if c.split(" : ", 1)[1].strip()]
    out.elements_de_recherche_examines = [
        "diagnostic méthodologique vérifié de l'étape 8",
        "question de recherche vérifiée", "objectifs de recherche vérifiés",
    ]
    if hypotheses:
        out.elements_de_recherche_examines.append("hypothèses de recherche vérifiées")
    if (request.university_instructions or "").strip():
        out.elements_de_recherche_examines.append("consignes de l'établissement fournies")
    # Champ DÉTERMINISTE : ce sont les références RÉELLEMENT récupérées, jamais ce que le modèle
    # prétend avoir lu. Il disait « aucune source en ligne consultée » — faux depuis que l'agent
    # va chercher lui-même ses références de méthode.
    if recherche is not None and recherche.records:
        out.sources_methodologiques_consultees = [
            (f"{r.title} ({r.year}) — {r.url}" if r.year else f"{r.title} — {r.url}").strip(" —")
            for r in recherche.records]
    else:
        note = getattr(recherche, "note", "") if recherche is not None else ""
        out.sources_methodologiques_consultees = [
            "recherche documentaire sans résultat exploitable"
            + (f" ({note})" if note else "")]
    out.limites_et_risques = [f"{l.description} — {l.consequence}".strip(" —")
                              for l in protocol.limites if str(l.description or "").strip()]
    out.contradictions = list(protocol.contradictions_diagnostic)
    out.unknowns = list(analysis.unknowns)
    if not protocol.contradictions_diagnostic and analysis.contradictions:
        # La contradiction est REPRISE, jamais corrigée en silence (SPEC §6).
        out.contradictions = list(analysis.contradictions)
    out.coherence_controls = protocol_checks.coherence_controls(request, protocol, matrix)
    # Les manques qui nient un élément fourni sont retirés des DEUX listes (sinon la contradiction
    # interne réapparaît : `elements_manquants` vs le socle présent).
    cleaned = _clean_missing(request, analysis.elements_manquants)
    analysis.elements_manquants = list(cleaned)
    out.analysis.elements_manquants = list(cleaned)
    for text in cleaned:
        if text not in out.missing_information:
            out.missing_information.append(text)
    out.document_status = (DocumentStatus.brouillon if out.missing_information
                           or out.contradictions else DocumentStatus.a_verifier)
    return out


def _derived_missing(request, analysis) -> list[str]:
    missing: list[str] = []
    if not (request.field_access or "").strip():
        missing.append("accès au terrain non confirmé")
    if not (request.available_data or "").strip():
        missing.append("origine des données à confirmer")
    missing.extend(_clean_missing(request, analysis.elements_manquants))
    seen: set[str] = set()
    return [m for m in missing if not (m in seen or seen.add(m))]


def _formulate(llm, request, annotations, analysis, limits, extra: str = "",
               max_attempts: int = 2, recherche=None, bloc_sources: str = ""):
    """Produit P2 → P3 → P4, applique les contrôles déterministes, re-tente si nécessaire."""
    attempts = 0
    out = None
    violations: list[str] = []
    extra_local = extra
    for _ in range(max(1, max_attempts)):
        protocol_out, used2 = protocol_stage.run_protocol(
            llm, request, annotations, analysis, extra=extra_local,
            sources_bloc=bloc_sources)
        attempts += used2
        instruments_out, used3 = instruments_stage.run(
            llm, request, annotations, protocol_out.protocol, extra=extra_local,
            sources_bloc=bloc_sources)
        attempts += used3
        writing_out, used4 = writing_stage.run(
            llm, request, annotations, protocol_out.protocol,
            matrix_rules.recompute_coverage(matrix_rules.build(request, instruments_out.matrice)),
            extra=extra_local)
        attempts += used4
        out = _assemble(request, analysis, protocol_out, instruments_out, writing_out,
                        recherche=recherche)
        violations = protocol_checks.run(request, out.protocol, out.matrice, out.draft,
                                         out.analysis)
        if not violations:
            return out, attempts, []
        extra_local = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                       + "\n".join(f"- {v}" for v in violations))
    return out, attempts, violations


def _run_verifier(out, verifier_llm, request, llm, annotations, analysis, settings, result):
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = MethodologyStatus.awaiting_human_validation
            out.document_status = DocumentStatus.en_attente_de_validation
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = MethodologyStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = MethodologyStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"
            return
        previous = current
        extra = ("Le vérificateur demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            new_out, used, violations = _formulate(
                llm, request, annotations, analysis, settings.limits, extra=extra)
        except PipelineError:
            out.status = MethodologyStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"
            return
        result.attempts += used
        if violations or new_out is None:
            out.status = MethodologyStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.protocol = new_out.protocol
        out.matrice = new_out.matrice
        out.draft = new_out.draft
        out.informations_a_confirmer = list(new_out.informations_a_confirmer)
        out.coherence_controls = protocol_checks.coherence_controls(
            request, out.protocol, out.matrice)
        out.document_status = DocumentStatus.a_verifier
        # Tout champ DÉRIVÉ est rafraîchi après reformulation (leçon de l'agent 7).
        out.confidence = _confidence(out)
        result.verifier_status = "corrections_requested"
    # La DERNIÈRE reformulation doit être JUGÉE (leçon du test de chaîne réel).
    verdict = verifier_module.verify(verifier_llm, request, out)
    result.verifier = verdict
    result.verifications += 1
    if verdict.verdict == VerifierVerdict.verified:
        out.verification_result.verified = True
        out.verification_result.verifier_status = "verified"
        out.status = MethodologyStatus.awaiting_human_validation
        out.document_status = DocumentStatus.en_attente_de_validation
        result.verifier_status = "verified"
    else:
        out.status = MethodologyStatus.verification_failed
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

    # L'AGENT VA CHERCHER (mission propre : des references de MÉTHODE, pas la litterature du sujet).
    # La recherche tourne AVANT les etages et son bloc est transmis a P1, P2 et P3 — la ou se
    # decident l'echantillon, les instruments et l'analyse. Un echec reseau est DECLARE, jamais fatal.
    if allow_network:
        recherche = research_stage.run(request, settings)
    else:
        recherche = research_stage.ResearchResult(
            note="recherche documentaire non lancée (réseau désactivé)")
    bloc_sources = recherche.bloc_prompt
    stages["recherche"] = {
        "references": len(recherche.records),
        "fournisseurs": recherche.providers_used,
        "echecs": recherche.providers_failed,
        "requetes": recherche.queries,
    }

    def checkpoint(name: str, payload) -> None:
        if persist:
            persist(name, payload)

    # [P1] analyse du dossier
    analysis, a1 = protocol_stage.run_analysis(llm, request, annotations,
                                              sources_bloc=bloc_sources)
    stages["analysis"] = {
        "disponible": len(analysis.elements_disponibles),
        "manquant": len(analysis.elements_manquants),
        "contradictions": len(analysis.contradictions),
    }
    checkpoint("analysis", analysis)

    # [P2 → P4] protocole, instruments, matrice, rédaction + contrôles déterministes
    out, a_rest, violations = _formulate(llm, request, annotations, analysis, settings.limits,
                                         recherche=recherche, bloc_sources=bloc_sources)
    attempts_total = a1 + a_rest
    if violations or out is None:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "protocole non conforme : " + " ; ".join(violations[:8]))
    stages["protocol"] = {
        "approche": out.protocol.approche, "type_recherche": out.protocol.type_recherche,
        "techniques": [t.nom for t in out.protocol.techniques],
        "objectifs_couverts": sum(1 for r in out.matrice.lignes
                                  if r.statut.value == "couverte"),
        "objectifs_total": len(out.matrice.lignes),
    }
    checkpoint("protocole", out)

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

    # [P5] VÉRIFICATEUR indépendant
    _run_verifier(out, verifier_llm, request, llm, annotations, analysis, settings, result)

    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme après vérification : " + " ; ".join(post[:8]))

    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=result.reformulations)
    out.confidence = _confidence(out)
    result.llm_calls = getattr(llm, "calls", 0)
    checkpoint("methodology_output", out)
    return result


def decide(request, settings, llm, output: MethodologyOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant / de l'encadreur (portillon humain)."""
    verifier_llm = verifier_llm or llm
    out, needs_revision, violations = decision_stage.apply(output, decision, request)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "protocole modifié non conforme : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_revision and out.status == MethodologyStatus.ready_for_verification:
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = MethodologyStatus.awaiting_human_validation
            out.document_status = DocumentStatus.en_attente_de_validation
            result.verifier_status = "verified"
        else:
            out.status = MethodologyStatus.verification_failed
            out.document_status = DocumentStatus.a_reviser
            result.verifier_status = "verification_failed"

    out.coherence_controls = protocol_checks.coherence_controls(request, out.protocol, out.matrice)
    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(post[:8]))
    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=1 if needs_revision else 0)
    out.confidence = _confidence(out)
    return result
