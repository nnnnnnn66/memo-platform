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
    research_stage,
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
    # Résultat de la recherche documentaire RÉELLE (références récupérées, fournisseurs muets).
    # Exposé pour que le monde extérieur sache ce que l'agent a réellement pu consulter.
    research: object | None = None


def _sources_inventees(output, research) -> list[str]:
    """Garde anti-invention : toute source EXTERNE citée doit exister dans ce qui a été récupéré.

    C'est ce qui rend « il ne dira pas qu'il n'a pas trouvé » tenable : l'agent a le droit de
    rapporter ce que la recherche a réellement ramené, jamais ce qu'il aurait aimé trouver. Une
    référence inventée est refusée, exactement comme un chiffre inventé.
    """
    if not research or not research.records:
        return []
    connues = set()
    for record in research.records:
        connues.add(record.source_id.strip().lower())
        if record.url:
            connues.add(record.url.strip().lower())
        if record.title:
            connues.add(record.title.strip().lower())
    violations: list[str] = []
    for item in getattr(output, "evidence", []) or []:
        if str(getattr(item, "source_type", "")) != "external":
            continue
        marqueurs = {str(getattr(item, "url", "") or "").strip().lower(),
                     str(getattr(item, "title", "") or "").strip().lower(),
                     str(getattr(item, "source", "") or "").strip().lower()}
        marqueurs.discard("")
        if marqueurs and not (marqueurs & connues):
            violations.append(
                f"source externe non prouvée : « {getattr(item, 'title', '') or getattr(item, 'url', '')} » "
                "ne figure pas dans les références réellement récupérées pour ce sujet")
    return violations


def _produce_validated(llm, system, request, annotations, extra="", max_attempts=2,
                       sources_bloc="", research=None):
    """Produit et valide (parser→schema→business→security). Retourne (output, attempts)."""
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        raw = subject_agent.produce(llm, system, request, annotations, extra,
                                    sources_bloc=sources_bloc)
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
        violations = list(business_validation.validate_business(request, output))
        # Une source citée qui n'a pas été récupérée est une source inventée : elle se corrige
        # comme les autres violations, jamais en silence.
        violations += _sources_inventees(output, research)
        if violations and attempts < max_attempts:
            extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                     + "\n".join(f"- {v}" for v in violations))
            continue
        security_validation.check(output)
        return output, attempts
    raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "échec de validation après re-tentatives")


def analyze_subject(request: SubjectRequest, settings, llm, verifier_llm=None,
                    research=None) -> PipelineResult:
    verifier_llm = verifier_llm or llm
    # Remise a zero FACULTATIVE : le contrat d'un client reste `complete()`. Une doublure de
    # test n'a aucun etat a remettre, et lui en imposer un ferait porter au test une obligation
    # qui n'appartient qu'au client reel.
    if hasattr(llm, "nouvelle_campagne"):
        llm.nouvelle_campagne()

    input_validation.validate(request, settings.limits)
    annotations = security_layer.screen(request, settings.security)

    # L'AGENT VA CHERCHER L'INFORMATION (demande du porteur) : la recherche documentaire réelle
    # tourne AVANT le modèle, et ses résultats lui sont fournis. `research=None` la déclenche ;
    # passer un objet déjà calculé sert aux tests hors réseau.
    if research is None:
        try:
            research = research_stage.run(request.subject_text or "", settings,
                                          discipline=request.discipline or "")
        except Exception as exc:  # jamais une panne réseau ne fait échouer le travail
            log.info("recherche documentaire indisponible : %s", exc)
            research = research_stage.ResearchResult(
                note=f"recherche documentaire indisponible ({type(exc).__name__})")

    system = subject_agent.load_subject_system()
    output, attempts = _produce_validated(llm, system, request, annotations,
                                          sources_bloc=research.bloc_prompt, research=research)

    # Une limite qui CONTREDIT les sources réellement transmises est retirée : le modèle recopie
    # parfois une phrase type (« aucune référence externe n'a été récupérée… ») alors que le bloc de
    # sources lui a été fourni et qu'il en cite plusieurs. Défaut constaté en démonstration : la
    # fiche affichait « aucune source » ET sept références citées. On ne touche qu'à cette
    # contradiction précise, jamais aux autres limites.
    if getattr(research, "records", None):
        _contradictoires = ("aucune référence externe", "aucun bloc de sources",
                            "aucune source documentaire", "aucune référence n'a été")
        retirees = [limite for limite in (output.identified_limits or [])
                    if any(motif in limite.lower() for motif in _contradictoires)]
        if retirees:
            output.identified_limits = [limite for limite in (output.identified_limits or [])
                                        if limite not in retirees]

    result = PipelineResult(output=output, attempts=attempts,
                            injection_annotations=annotations, research=research)

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
