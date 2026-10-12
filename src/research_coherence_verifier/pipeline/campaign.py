"""Orchestrateur de l'Agent 13 — Vérificateur global de cohérence (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → ÉTAT DU DOSSIER (détermin.) → FAITS X1–X12 (détermin.)
      → P1 audit transversal (LLM) → P2 rapport et PORTÉE (LLM)
      → contrôles Y1–Y5 → validations T1–T6 → sécurité
      → CONTRÔLEUR DE L'AUDIT (C1–C13) → PORTILLON HUMAIN.

Deux règles structurantes :
- **le programme établit les faits, le modèle juge les liens** ;
- **aucun constat sans preuve**, et **la portée est toujours déclarée** (ce que l'agent ne peut pas
  vérifier).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..analysis import scope
from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.audit import Finding, Origine, Severite, Suite
from ..schemas.common import Confidence
from ..schemas.decision import DecisionRequest
from ..schemas.output import (
    AuditStatus,
    CoherenceOutput,
    DocumentStatus,
    Evidence,
)
from ..schemas.report import (
    CoherenceReport,
    Recommandation,
    verdict_from,
    verdict_justification,
)
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    audit_stage,
    business_validation,
    coherence_checks,
    decision_stage,
    facts_stage,
    input_controller,
    input_validation,
    prerequisites,
    report_stage,
    security_layer,
    security_validation,
    verifier as verifier_module,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: CoherenceOutput
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


def _confidence(output: CoherenceOutput) -> Confidence:
    """Confiance DÉTERMINÉE par ce que l'audit a pu établir, avec la rationale qui ÉNONCE son calcul."""
    base = 0.5
    termes = [f"base {base:.2f}"]
    if output.etapes_absentes:
        base -= min(0.25, 0.03 * len(output.etapes_absentes))
        termes.append(f"− {min(0.25, 0.03 * len(output.etapes_absentes)):.2f} "
                      f"({len(output.etapes_absentes)} étape(s) absente(s) : audit partiel)")
    if output.etapes_non_verifiees:
        base -= min(0.15, 0.05 * len(output.etapes_non_verifiees))
        termes.append(f"− {min(0.15, 0.05 * len(output.etapes_non_verifiees)):.2f} "
                      f"({len(output.etapes_non_verifiees)} étape(s) non vérifiée(s))")
    if output.audit.constats_infirmes:
        base -= 0.05
        termes.append("− 0.05 (faits infirmés par l'examen sémantique)")
    if output.verification_result.verified:
        base += 0.2
        termes.append("+ 0.20 (contrôle de l'audit réussi)")
    if output.non_verifiable:
        base += 0.05
        termes.append(f"+ 0.05 (portée déclarée : {len(output.non_verifiable)} élément(s) non "
                      "vérifiable(s))")
    overall = round(max(0.0, min(1.0, base)), 2)
    rationale = (
        f"{len(output.etapes_presentes)} étape(s) examinée(s) ; "
        f"{len(output.audit.constats)} constat(s) ; verdict « {output.report.verdict.value} » ; "
        f"calcul : {' '.join(termes)} = {overall:.2f}")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, dossier, questions, notes) -> CoherenceOutput:
    return CoherenceOutput(
        status=AuditStatus.needs_clarification,
        document_status=DocumentStatus.brouillon,
        research_id=f"{request.student_id}/{request.session_id or ''}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        etapes_presentes=dossier.etapes_presentes,
        etapes_non_verifiees=dossier.etapes_non_verifiees,
        etapes_absentes=dossier.etapes_absentes,
        elements_de_service=dossier.elements_de_service,
        report=CoherenceReport(synthese="Audit non conduit : dossier insuffisant.",
                               verdict=verdict_from([]),
                               verdict_justification="aucun constat"),
        non_verifiable=scope.portee_complete(dossier.etapes_absentes),
        questions_for_human=questions,
        limites_de_cet_audit=notes,
    )


def _consolidate(faits: list[Finding], audit_output) -> tuple[list[Finding], list[Finding]]:
    """Fusionne faits déterministes et constats sémantiques.

    Un fait ne peut pas être SUPPRIMÉ : s'il est infirmé, il est déplacé dans `constats_infirmes` avec
    son motif (contrôle Y2).
    """
    infirmes_codes = {str(c).strip() for c in audit_output.faits_infirmes if str(c).strip()}
    motif = (audit_output.motifs or [""])[0]
    constats: list[Finding] = []
    infirmes: list[Finding] = []
    for fait in faits:
        if fait.code in infirmes_codes:
            copie = fait.model_copy(update={"suite": Suite.infirme, "motif_suite": motif})
            infirmes.append(copie)
        else:
            constats.append(fait)
    for item in audit_output.constats:
        constats.append(Finding(
            code=str(item.code or "LIBRE"), axe=item.axe, severite=item.severite,
            elements=item.elements, constat=item.constat, preuve=item.preuve,
            recommandation=item.recommandation, origine=Origine.llm))
    return constats, infirmes


def _recommandations(constats: list[Finding], model_report: CoherenceReport) -> list[Recommandation]:
    """Les recommandations du modèle, complétées par le programme pour tout constat non couvert."""
    out = [r for r in model_report.recommandations if str(r.action or "").strip()]
    couverts = {str(r.code).strip() for r in out if str(r.code).strip()}
    for constat in constats:
        if constat.severite == Severite.mineur:
            continue
        if constat.code and constat.code in couverts:
            continue
        if constat.recommandation:
            out.append(Recommandation(code=constat.code, action=constat.recommandation))
    return out


def _assemble(request, dossier, constats, infirmes, model_report, supplement) -> CoherenceOutput:
    verdict = verdict_from(constats)
    noms_absents = [e.split(" ", 1)[1] if " " in e else e for e in dossier.etapes_absentes]
    portee = scope.portee_complete(noms_absents, supplement)
    report = CoherenceReport(
        synthese=str(model_report.synthese or "").strip(),
        constats=constats,
        recommandations=_recommandations(constats, model_report),
        non_verifiable=portee,
        verdict=verdict,
        verdict_justification=verdict_justification(constats, verdict),
    )
    output = CoherenceOutput(
        status=AuditStatus.ready_for_verification,
        document_status=DocumentStatus.brouillon,
        research_id=f"{request.student_id}/{request.session_id or ''}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        version_elements_consultes=[f"étape {e} ({'vérifiée' if e in dossier.etapes_verifiees else 'non vérifiée'})"
                                     for e in dossier.etapes_presentes],
        etapes_presentes=dossier.etapes_presentes,
        etapes_non_verifiees=dossier.etapes_non_verifiees,
        etapes_absentes=dossier.etapes_absentes,
        elements_de_service=dossier.elements_de_service,
        document_version="1.0",
        report=report,
        non_verifiable=portee,
        coherence_controls=_controles_lisibles(dossier, constats, portee),
    )
    output.audit.dossier = dossier
    output.audit.constats = constats
    output.audit.constats_infirmes = infirmes
    return output


def _controles_lisibles(dossier, constats, portee) -> list[str]:
    controles = [f"{len(dossier.etapes_presentes)} étape(s) examinée(s) sur 11"]
    if dossier.etapes_absentes:
        controles.append(f"{len(dossier.etapes_absentes)} étape(s) absente(s) : liens correspondants "
                         "non examinés")
    if dossier.etapes_non_verifiees:
        controles.append(f"{len(dossier.etapes_non_verifiees)} étape(s) non vérifiée(s) : l'audit "
                         "porte sur des contenus non contrôlés")
    compte = {niveau.value: sum(1 for c in constats if c.severite == niveau)
              for niveau in (Severite.bloqueur, Severite.majeur, Severite.mineur)}
    controles.append(f"constats : {compte['bloqueur']} bloquant(s), {compte['majeur']} majeur(s), "
                     f"{compte['mineur']} mineur(s)")
    controles.append(f"{len(portee)} élément(s) déclaré(s) non vérifiable(s) — la portée est "
                     "explicite dans le rapport")
    return controles


def _formulate(llm, request, annotations, dossier, faits, extra: str = "", max_attempts: int = 2):
    """Produit P1 → P2 et applique les contrôles Y1–Y5."""
    attempts = 0
    out = None
    violations: list[str] = []
    extra_local = extra
    for _ in range(max(1, max_attempts)):
        audit_output, used1 = audit_stage.run(llm, request, annotations, dossier, faits,
                                              extra=extra_local)
        attempts += used1
        constats, infirmes = _consolidate(faits, audit_output)
        noms_absents = [e.split(" ", 1)[1] if " " in e else e for e in dossier.etapes_absentes]
        portee = scope.portee_complete(noms_absents)
        report_output, used2 = report_stage.run(llm, request, annotations, dossier, faits,
                                                audit_output.constats, portee, extra=extra_local)
        attempts += used2
        out = _assemble(request, dossier, constats, infirmes, report_output.report,
                        report_output.non_verifiable_supplementaire)
        out.audit.constats = constats
        out.audit.constats_infirmes = infirmes
        violations = coherence_checks.run(
            out.audit.constats, faits, infirmes, out.non_verifiable, out.report.verdict)
        if not violations:
            return out, attempts, []
        extra_local = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                       + "\n".join(f"- {v}" for v in violations[:8]))
    return out, attempts, violations


def _run_verifier(out, verifier_llm, request, llm, annotations, settings, result, faits):
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = AuditStatus.awaiting_human_validation
            out.document_status = DocumentStatus.en_attente_de_validation
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = AuditStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = AuditStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"
            return
        previous = current
        extra = ("Le contrôleur de l'audit demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            new_out, used, violations = _formulate(llm, request, annotations, out.audit.dossier,
                                                   faits, extra=extra)
        except PipelineError:
            out.status = AuditStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"
            return
        result.attempts += used
        if violations or new_out is None:
            out.status = AuditStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.report = new_out.report
        out.audit = new_out.audit
        out.non_verifiable = new_out.non_verifiable
        out.coherence_controls = new_out.coherence_controls
        out.document_status = DocumentStatus.a_corriger
        out.corrections_effectuees.append(
            "corrections appliquées après contrôle : " + " ; ".join(verdict.corrections[:5]))
        result.verifier_status = "corrections_requested"
    verdict = verifier_module.verify(verifier_llm, request, out)
    result.verifier = verdict
    result.verifications += 1
    if verdict.verdict == VerifierVerdict.verified:
        out.verification_result.verified = True
        out.verification_result.verifier_status = "verified"
        out.status = AuditStatus.awaiting_human_validation
        out.document_status = DocumentStatus.en_attente_de_validation
        result.verifier_status = "verified"
    else:
        out.status = AuditStatus.verification_failed
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
    input_controller.prepare(request)
    input_controller.check_upstream(request)

    pre = prerequisites.check(request)
    if pre["needs_clarification"]:
        output = _clarification_output(request, pre["dossier"], pre["questions"], pre["defaults_used"])
        return CampaignResult(output=output, stages={"prerequisites": pre})

    annotations = security_layer.screen(request, settings.security)

    def checkpoint(name: str, payload) -> None:
        if persist:
            persist(name, payload)

    dossier, faits = facts_stage.faits(request)
    stages["dossier"] = {"presentes": len(dossier.etapes_presentes),
                         "absentes": len(dossier.etapes_absentes),
                         "non_verifiees": len(dossier.etapes_non_verifiees)}
    stages["faits"] = {f.code: f.severite.value for f in faits}
    checkpoint("coherence_faits", {"dossier": dossier.model_dump(), "faits": [f.model_dump() for f in faits]})

    out, attempts_total, violations = _formulate(llm, request, annotations, dossier, faits)
    if violations or out is None:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "audit non conforme : " + " ; ".join(violations[:8]))
    verifier_module.ensure_verdict_consistent(out)
    checkpoint("coherence_audit", out)

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

    _run_verifier(out, verifier_llm, request, llm, annotations, settings, result, faits)

    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme après contrôle : " + " ; ".join(post[:8]))

    out.evidence = Evidence(
        llm_calls=getattr(llm, "calls", 0), network_requests=0,
        reformulations=result.reformulations, constats=len(out.audit.constats),
        constats_deterministes=sum(1 for c in out.audit.constats
                                   if (getattr(c.origine, "value", c.origine) == "deterministe")),
        constats_semantiques=sum(1 for c in out.audit.constats
                                 if (getattr(c.origine, "value", c.origine) == "llm")))
    out.confidence = _confidence(out)
    result.llm_calls = getattr(llm, "calls", 0)
    checkpoint("coherence_report", out)
    return result


def decide(request, settings, llm, output: CoherenceOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant (portillon humain, SPEC §12)."""
    verifier_llm = verifier_llm or llm
    out, needs_recontrole, violations = decision_stage.apply(output, decision, request)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "audit révisé non conforme : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_recontrole and out.status == AuditStatus.ready_for_verification:
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = AuditStatus.awaiting_human_validation
            out.document_status = DocumentStatus.en_attente_de_validation
            result.verifier_status = "verified"
        else:
            out.status = AuditStatus.verification_failed
            out.document_status = DocumentStatus.a_corriger
            result.verifier_status = "verification_failed"

    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=1 if needs_recontrole else 0,
                            constats=len(out.audit.constats))
    out.confidence = _confidence(out)
    return result
