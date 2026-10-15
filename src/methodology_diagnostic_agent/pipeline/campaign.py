"""Orchestrateur du diagnostic méthodologique (SPEC §9).

Enchaînement :
    pré-cadrage → sécurité → LLM P1 (analyse du dossier) → LLM P2 (diagnostic)
      → contrôles déterministes M1–M7 → contrôles de cohérence et de faisabilité
      → clarification documentaire (optionnelle) → validations
      → VÉRIFICATEUR indépendant → PORTILLON HUMAIN (décision étudiante / encadreur).
Le diagnostic reste PROVISOIRE tant que des informations manquent. Le statut `validated` n'est jamais
posé par l'agent : il vient de la décision humaine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..analysis import methodology_rules as rules
from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence
from ..schemas.decision import DecisionRequest
from ..schemas.methodology import DiagnosticStatusEnum
from ..schemas.output import Evidence, MethodologyOutput, MethodologyStatus
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    analysis_stage,
    business_validation,
    clarification_stage,
    decision_stage,
    diagnosis_checks,
    diagnosis_stage,
    input_controller,
    input_validation,
    prerequisites,
    security_layer,
    security_validation,
    verifier as verifier_module,
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


def _alternatives_overview(diagnosis) -> list[str]:
    """Récapitule les alternatives DÉJÀ proposées dans chaque catégorie — aucune invention.

    Le champ existait dans le schéma sans jamais être rempli : le vérificateur l'a relevé en
    campagne réelle (« alternatives_overview vide alors que des alternatives figurent dans chaque
    catégorie »). On agrège donc ce qui existe déjà, sans rien ajouter.
    """
    lignes: list[str] = []
    choix = [("approche", diagnosis.approche), ("logique", diagnosis.logique),
             ("type de recherche", diagnosis.type_recherche), ("stratégie", diagnosis.strategie)]
    choix += [(f"collecte {i}", c) for i, c in enumerate(diagnosis.collecte, 1)]
    choix += [(f"analyse {i}", c) for i, c in enumerate(diagnosis.analyse, 1)]
    for nom, choice in choix:
        alts = [str(a).strip() for a in (choice.alternatives or []) if str(a).strip()]
        if alts:
            propositions = ", ".join(f"« {a} »" for a in alts)
            lignes.append(f"{nom} — « {(choice.proposition or '').strip()} » : "
                          f"alternative(s) {propositions}")
    return lignes


def _confidence(output: MethodologyOutput) -> Confidence:
    """Confiance DÉTERMINÉE par les preuves (jamais auto-attribuée au hasard).

    La rationale ÉNONCE le calcul terme à terme : le vérificateur signale un `overall` nu,
    affirmé sans règle (« confidence.overall est affirmée sans règle de calcul explicite ») —
    leçon déjà rencontrée sur l'agent 4.
    """
    base = 0.5
    termes = [f"base {base:.2f}"]
    if output.provisional:
        base -= 0.15
        termes.append("− 0.15 (diagnostic provisoire)")
    if output.feasibility_controls:
        base -= 0.05
        termes.append("− 0.05 (faisabilité à contrôler)")
    verified = 0.2 if output.verification_result.verified else 0.0
    if verified:
        termes.append("+ 0.20 (vérification indépendante réussie)")
    penalty = 0.06 * len(output.ambiguities) + 0.05 * len(output.missing_information)
    if penalty:
        termes.append(f"− {penalty:.2f} ({len(output.ambiguities)} ambiguïté(s), "
                      f"{len(output.missing_information)} manque(s) bloquant(s))")
    overall = round(max(0.0, min(1.0, base + verified - penalty)), 2)
    # Les inconnues déclarées sont ANNONCÉES dans la rationale : ne pas les mentionner produisait
    # « 0 information manquante » en contradiction avec une liste `unknowns` bien remplie (relevé
    # par le vérificateur). Elles pèsent déjà sur la confiance via `provisional` (inconnues ⇒
    # diagnostic provisoire), on ne les recompte donc pas dans la pénalité par élément.
    inconnues = f", {len(output.unknowns)} inconnue(s) déclarée(s)" if output.unknowns else ""
    rationale = (
        f"{'diagnostic provisoire' if output.provisional else 'diagnostic appuyé'} ; "
        f"vérification indépendante : {'réussie' if output.verification_result.verified else 'non acquise'} ; "
        f"{len(output.ambiguities)} ambiguïté(s), {len(output.missing_information)} information(s) manquante(s)"
        f"{inconnues} ; calcul : {' '.join(termes)} = {overall:.2f}")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, questions: list[str], notes: list[str]) -> MethodologyOutput:
    return MethodologyOutput(
        status=MethodologyStatus.needs_clarification,
        diagnostic_status=DiagnosticStatusEnum.provisoire,
        provisional=True,
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        clarification_questions=questions,
        limits_of_this_output=notes,
    )


# --- Une seule question autorisée : le TERRAIN (consigne du porteur, prioritaire) -------------
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


def _questions_de_terrain(questions):
    """Seules les questions de TERRAIN sont rendues à l'étudiante (consigne du porteur)."""
    return [q for q in questions if _est_question_de_terrain(q)]


def _declarer_choix(out, questions) -> None:
    """Un choix de méthode est TRANCHÉ par l'agent et DÉCLARÉ, jamais demandé à l'étudiante."""
    for question in questions:
        if not _est_question_de_terrain(question):
            out.limits_of_this_output.append(
                "Choix tranché par l'agent (à corriger en reprenant l'étape si nécessaire) : "
                + str(question))


def _coherence_summary(output: MethodologyOutput) -> list[str]:
    """Contrôles de cohérence rendus lisibles pour l'étudiant (SPEC §16).

    Formulés en français clair : les codes internes (M1–M7) parlaient au développeur, pas à
    l'étudiant — signalé par le vérificateur en campagne réelle (« libellés d'outillage peu
    lisibles »).
    """
    diag = output.diagnosis
    checks = [
        "Les six catégories (approche, logique de raisonnement, type de recherche, stratégie, "
        "collecte, analyse) sont distinctes et chacune est justifiée.",
        f"Cohérence vérifiée entre l'approche « {diag.approche.code} », les techniques de collecte "
        "et les méthodes d'analyse.",
        "Causalité : "
        + ("un dispositif expérimental est déclaré." if rules.causality_is_justified(diag.strategie.code)
           else "aucune lecture causale n'est proposée sans dispositif expérimental."),
    ]
    if output.hypotheses_examined:
        checks.append("Hypothèses du dossier prises en charge par la méthodologie proposée : "
                      f"{len(output.hypotheses_examined)}.")
    return checks


def _assemble(request, pre, analysis, diagnosis_stage_out, missing) -> MethodologyOutput:
    out = MethodologyOutput(
        status=MethodologyStatus.ready_for_verification,
        diagnostic_status=DiagnosticStatusEnum.en_attente_de_validation,
        research_id=f"{request.student_id}/{request.session_id or ''}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        subject=request.effective_subject(),
        main_research_question=request.effective_question(),
        secondary_research_questions=request.effective_secondary_questions(),
        general_objective=request.effective_general_objective(),
        specific_objectives=request.effective_specific_objectives(),
        resume=diagnosis_stage_out.resume,
        analysis=analysis,
        diagnosis=diagnosis_stage_out.diagnosis,
        hypotheses_examined=list(diagnosis_stage_out.hypotheses_examined),
        feasibility_controls=list(diagnosis_stage_out.feasibility_controls),
        unknowns=list(diagnosis_stage_out.unknowns),
        limits_of_this_output=list(diagnosis_stage_out.limits_of_this_output),
        questions_for_human=_questions_de_terrain(diagnosis_stage_out.questions_for_human),
    )
    # `unknowns` (déclaration brute du modèle) et `missing_information` (manques DÉDUITS du dossier)
    # restent deux listes distinctes, comme chez les agents 6 et 7 — où `missing_information` ne
    # porte que les manques bloquants, la confiance étant pénalisée par élément (0.05). Les
    # fusionner a été essayé : le vérificateur signalait alors une « incohérence formelle » dans
    # l'autre sens, et la confiance tombait à 0.1 sur un diagnostic pourtant vérifié 13/13.
    out.provisional = bool(missing)
    out.missing_information = list(missing)
    out.coherence_controls = _coherence_summary(out)
    # Récapitulatif des alternatives DÉJÀ proposées par catégorie (champ du schéma qui restait vide).
    out.alternatives_overview = _alternatives_overview(out.diagnosis)
    out.tools_and_documents = [
        "Dossier de recherche transmis par les agents amont (sujet, question, objectifs, hypothèses)",
        "Aucune recherche documentaire en ligne effectuée" if not out.source_evidence
        else "Recherche documentaire bornée (clarification)",
    ]
    # Les points de vigilance de l'analyse sont consignés comme points à clarifier (jamais comme
    # `ambiguities` bloquantes) : la cohérence interne de la sortie a été un piège réel (agent 7).
    for text in [str(a).strip() for a in analysis.elements_manquants if str(a).strip()]:
        if text not in out.missing_information:
            out.missing_information.append(text)
    for text in [str(a).strip() for a in analysis.contradictions if str(a).strip()]:
        out.limits_of_this_output.append("contradiction relevée : " + text)
    # Un diagnostic est « provisoire » dès qu'il reste des informations manquantes OU des
    # inconnues déclarées : c'est ce que le modèle écrit lui-même dans son résumé, et sans quoi
    # le champ contredisait le texte (relevé par le vérificateur, campagne réelle de l'agent 8).
    out.provisional = bool(out.missing_information or out.unknowns)
    analysis.elements_manquants = []
    out.analysis.elements_manquants = []
    return out


def _derived_missing(request, analysis, diagnosis_stage_out) -> list[str]:
    missing: list[str] = []
    if not (request.available_data or "").strip():
        missing.append("données disponibles non précisées (faisabilité à confirmer)")
    if not (request.field_access or "").strip():
        missing.append("accès au terrain non confirmé")
    if not (request.available_resources or "").strip():
        missing.append("ressources (temps, budget, moyens) non précisées")
    missing.extend(str(a).strip() for a in analysis.elements_manquants if str(a).strip())
    seen: set[str] = set()
    return [m for m in missing if not (m in seen or seen.add(m))]


def _formulate(llm, request, annotations, analysis, limits, extra: str = "", max_attempts: int = 2):
    """Produit le diagnostic, normalise les codes, avec re-tentative correctrice."""
    attempts = 0
    obj = None
    violations: list[str] = []
    extra_local = extra
    for _ in range(max(1, max_attempts)):
        obj, used = diagnosis_stage.run(
            llm, request, annotations, analysis, limits, extra=extra_local)
        attempts += used
        diag = obj.diagnosis
        for name, choice in (("approche", diag.approche), ("logique", diag.logique),
                             ("type_recherche", diag.type_recherche), ("strategie", diag.strategie)):
            choice.code = rules.normalize_code(choice.code or choice.proposition, name)
        missing = _derived_missing(request, analysis, obj)
        provisional = _assemble(request, {"defaults_used": []}, analysis, obj, missing)
        violations = diagnosis_checks.apply(provisional, request)
        if not violations:
            return obj, attempts, []
        extra_local = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                       + "\n".join(f"- {v}" for v in violations))
    return obj, attempts, violations


def _run_verifier(out, verifier_llm, request, pre, llm, annotations, analysis, settings,
                  result: CampaignResult) -> None:
    previous: set[str] | None = None
    for verification in range(1, settings.limits.max_verification_retries + 1):
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = verification
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = MethodologyStatus.awaiting_human_validation
            out.diagnostic_status = DiagnosticStatusEnum.en_attente_de_validation
            result.verifier_status = "verified"
            return
        if verdict.verdict == VerifierVerdict.rejected:
            out.status = MethodologyStatus.verification_failed
            out.diagnostic_status = DiagnosticStatusEnum.a_reviser
            result.verifier_status = "rejected"
            return
        current = set(verdict.corrections)
        if previous is not None and current and current == previous:
            out.status = MethodologyStatus.verification_failed
            out.diagnostic_status = DiagnosticStatusEnum.a_reviser
            result.verifier_status = "verification_failed"
            return
        previous = current
        extra = ("Le vérificateur demande des corrections :\n"
                 + "\n".join(f"- {c}" for c in verdict.corrections))
        try:
            obj, used, violations = _formulate(
                llm, request, annotations, analysis, settings.limits, extra=extra)
        except PipelineError:
            out.status = MethodologyStatus.verification_failed
            out.diagnostic_status = DiagnosticStatusEnum.a_reviser
            result.verifier_status = "verification_failed"
            return
        result.attempts += used
        if violations:
            out.status = MethodologyStatus.verification_failed
            out.diagnostic_status = DiagnosticStatusEnum.a_reviser
            result.verifier_status = "verification_failed"
            return
        result.reformulations += 1
        out.diagnosis = obj.diagnosis
        out.resume = obj.resume
        out.hypotheses_examined = list(obj.hypotheses_examined)
        out.feasibility_controls = list(obj.feasibility_controls)
        out.unknowns = list(obj.unknowns)
        out.limits_of_this_output = list(obj.limits_of_this_output)
        out.questions_for_human = _questions_de_terrain(obj.questions_for_human)
        _declarer_choix(out, obj.questions_for_human)
        out.coherence_controls = _coherence_summary(out)
        out.alternatives_overview = _alternatives_overview(out.diagnosis)
        # Confiance recalculée après reformulation (cohérence interne — leçon de l'agent 7).
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
        out.status = MethodologyStatus.awaiting_human_validation
        out.diagnostic_status = DiagnosticStatusEnum.en_attente_de_validation
        result.verifier_status = "verified"
    else:
        out.status = MethodologyStatus.verification_failed
        out.diagnostic_status = DiagnosticStatusEnum.a_reviser
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

    # [1] P1 — analyse du dossier
    analysis, a1 = analysis_stage.run(llm, request, annotations, settings.limits)
    stages["analysis"] = {"visee": analysis.visee[:160], "provenance": analysis.provenance.value}
    checkpoint("analysis", analysis)

    # [2-3] P2 — diagnostic et contrôles déterministes
    obj, a2, violations = _formulate(llm, request, annotations, analysis, settings.limits)
    attempts_total = a1 + a2
    if violations:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "diagnostic non conforme : " + " ; ".join(violations[:8]))
    stages["diagnosis"] = {"approche": obj.diagnosis.approche.code,
                           "logique": obj.diagnosis.logique.code,
                           "strategie": obj.diagnosis.strategie.code}

    missing = _derived_missing(request, analysis, obj)
    out = _assemble(request, pre, analysis, obj, missing)

    # [10] clarification documentaire (optionnelle, réseau borné)
    evidence = []
    clarif_stats = {"network_requests": 0, "cache_hits": 0}
    if allow_network:
        terms = [a.description.strip() for a in out.ambiguities if a.description.strip()]
        evidence, clarif_stats, clarif_note = clarification_stage.run(terms, settings)
        stages["clarification"] = {"note": clarif_note, "results": len(evidence)}
    out.source_evidence = evidence
    out.tools_and_documents = [
        "Dossier de recherche transmis par les agents amont (sujet, question, objectifs, hypothèses)",
        ("Recherche documentaire bornée (clarification) : " + str(len(evidence)) + " référence(s)")
        if evidence else "Aucune recherche documentaire en ligne effectuée",
    ]
    checkpoint("diagnosis_proposal", out)

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
    checkpoint("methodology_output", out)
    return result


def decide(request, settings, llm, output: MethodologyOutput, decision: DecisionRequest,
           verifier_llm=None) -> CampaignResult:
    """Applique la décision de l'étudiant / de l'encadreur (portillon humain)."""
    verifier_llm = verifier_llm or llm
    out, needs_revision, violations = decision_stage.apply(output, decision, request)
    if violations:
        raise PipelineError(ErrorState.INVALID_INPUT,
                            "diagnostic modifié non conforme : " + " ; ".join(violations))

    result = CampaignResult(output=out)
    if needs_revision and out.status == MethodologyStatus.ready_for_verification:
        verdict = verifier_module.verify(verifier_llm, request, out)
        result.verifier = verdict
        result.verifications = 1
        if verdict.verdict == VerifierVerdict.verified:
            out.verification_result.verified = True
            out.verification_result.verifier_status = "verified"
            out.status = MethodologyStatus.awaiting_human_validation
            out.diagnostic_status = DiagnosticStatusEnum.en_attente_de_validation
            result.verifier_status = "verified"
        else:
            out.status = MethodologyStatus.verification_failed
            out.diagnostic_status = DiagnosticStatusEnum.a_reviser
            result.verifier_status = "verification_failed"

    out.coherence_controls = _coherence_summary(out)
    post = business_validation.validate_semantics(out, request)
    post += business_validation.validate_final(out)
    if post:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(post[:8]))
    out.evidence = Evidence(llm_calls=getattr(llm, "calls", 0), network_requests=0,
                            reformulations=1 if needs_revision else 0)
    out.confidence = _confidence(out)
    return result
