"""Orchestrateur du pipeline Agent Sujet : garde-fous → vérificateur (SPEC §25, §34, §38).

Rien d'un LLM n'est utilisé avant Parser → Schema → Business → Security.
"""

from dataclasses import dataclass, field

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.input import SubjectRequest
from ..schemas.output import SubjectOutput, SubjectStatus
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    business_validation,
    input_validation,
    output_parser,
    schema_validation,
    security_layer,
    security_validation,
    subject_agent,
    subject_verifier,
)

log = get_logger("pipeline")


@dataclass
class PipelineResult:
    output: SubjectOutput
    verifier: VerifierOutput | None = None
    verifier_status: str = "pending"
    attempts: int = 0
    verifications: int = 0
    injection_annotations: list = field(default_factory=list)


def _produce_validated(llm, system, request, annotations, extra="", max_attempts=2):
    """Produit et valide (parser→schema→business→security). Retourne (output, attempts)."""
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        raw = subject_agent.produce(llm, system, request, annotations, extra)
        try:
            data = output_parser.extract_json(raw)
            output = schema_validation.validate(data)
        except PipelineError as exc:
            if attempts < max_attempts:
                extra = (f"Ta sortie précédente était invalide ({exc.state.value}). "
                         f"Détail : {exc.detail[:600]}\n"
                         "Réémets UNIQUEMENT un objet JSON conforme au schéma, sans texte autour.")
                continue
            raise
        violations = business_validation.validate_business(request, output)
        if violations and attempts < max_attempts:
            extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                     + "\n".join(f"- {v}" for v in violations))
            continue
        security_validation.check(output)
        return output, attempts
    raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "échec de validation après re-tentatives")


def analyze_subject(request: SubjectRequest, settings, llm, verifier_llm=None) -> PipelineResult:
    verifier_llm = verifier_llm or llm
    # Remise a zero FACULTATIVE : le contrat d'un client reste `complete()`. Une doublure de
    # test n'a aucun etat a remettre, et lui en imposer un ferait porter au test une obligation
    # qui n'appartient qu'au client reel.
    if hasattr(llm, "nouvelle_campagne"):
        llm.nouvelle_campagne()

    input_validation.validate(request, settings.limits)
    annotations = security_layer.screen(request, settings.security)

    system = subject_agent.load_subject_system()
    output, attempts = _produce_validated(llm, system, request, annotations)

    result = PipelineResult(output=output, attempts=attempts,
                            injection_annotations=annotations)

    # Vérificateur indépendant — uniquement si l'agent se déclare prêt.
    if output.status == SubjectStatus.ready_for_verification:
        reformulated = False
        for v in range(1, settings.limits.max_verification_retries + 1):
            verdict = subject_verifier.verify(verifier_llm, request, output)
            result.verifier = verdict
            result.verifications = v
            reformulated = False
            if verdict.verdict == VerifierVerdict.verified:
                output.validation.verified = True
                output.validation.verifier_status = "verified"
                result.verifier_status = "verified"
                break
            if verdict.verdict == VerifierVerdict.rejected:
                result.verifier_status = "rejected"
                break
            # corrections_requested → l'agent corrige
            extra = ("Le vérificateur demande des corrections :\n"
                     + "\n".join(f"- {c}" for c in verdict.corrections))
            try:
                output, extra_attempts = _produce_validated(
                    llm, system, request, annotations, extra, max_attempts=2)
                attempts += extra_attempts
                result.output = output
                result.verifier_status = "corrections_requested"
                reformulated = True
            except PipelineError:
                result.verifier_status = "verification_failed"
                break
        else:
            result.verifier_status = "verification_failed"

        # La DERNIÈRE reformulation n'était jamais jugée : la boucle sortait sur
        # `verification_failed` alors que la version corrigée peut passer (leçon du test de chaîne
        # réel). Une vérification finale tranche, sans nouvelle reformulation.
        if reformulated:
            verdict = subject_verifier.verify(verifier_llm, request, output)
            result.verifier = verdict
            result.verifications += 1
            if verdict.verdict == VerifierVerdict.verified:
                output.validation.verified = True
                output.validation.verifier_status = "verified"
                result.verifier_status = "verified"
            else:
                result.verifier_status = "verification_failed"
    return result
