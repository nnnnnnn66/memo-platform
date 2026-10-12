"""Orchestrateur de l'Agent Problème de recherche.

Enchaînement (SPEC §9, §10.12, §12) :
    entrées → sécurité → LLM phase 1 (analyse + requêtes)
           → SOURCE RETRIEVAL (déterministe)
           → LLM phase 2 (formulation ancrée)
           → Parser → Schéma → Métier → Sécurité
           → VÉRIFICATEUR indépendant → statut `verified` posé par lui seul.
"""

from dataclasses import dataclass, field

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.input import ProblemRequest
from ..schemas.output import ProblemOutput, ProblemStatus, SourceType, VerificationStatus
from ..schemas.search_intent import Phase1Output
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from ..sources.cache import SourceCache
from ..sources.http import Fetcher
from ..sources.registry import Registry
from ..sources.source_set import SourceSet
from . import (
    business_validation,
    input_validation,
    output_parser,
    problem_agent,
    problem_verifier,
    schema_validation,
    security_layer,
    security_validation,
    sources_stage,
)

log = get_logger("pipeline.orchestrator")


@dataclass
class PipelineResult:
    output: ProblemOutput
    verifier: VerifierOutput | None = None
    verifier_status: str = "pending"
    source_set: SourceSet | None = None
    phase1: Phase1Output | None = None
    attempts: int = 0
    verifications: int = 0
    injection_annotations: list = field(default_factory=list)
    external_requests: int = 0
    cache_hits: int = 0

    @property
    def source_ids(self) -> list[str]:
        return [r.source_id for r in (self.source_set.records if self.source_set else [])]


def _produce_phase1(llm, system, request, annotations, limits, extra="", max_attempts=2):
    """Analyse + intentions de recherche, validées avant tout accès réseau."""
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            raw = problem_agent.phase1(llm, system, request, annotations, extra)
            data = output_parser.extract_json(raw)
            phase1 = schema_validation.validate_phase1(data)
        except PipelineError as exc:
            if attempts < max_attempts:
                extra = (f"Ta sortie précédente était invalide ({exc.state.value}). "
                         f"Détail : {exc.detail[:600]}\n"
                         "Réémets UNIQUEMENT un objet JSON conforme au schéma, sans texte autour.")
                continue
            raise
        violations = business_validation.validate_phase1(phase1, limits)
        if violations:
            if attempts < max_attempts:
                extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                         + "\n".join(f"- {v}" for v in violations))
                continue
            raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                                "phase 1 non conforme : " + " ; ".join(violations))
        if not phase1.search_intents:
            phase1 = phase1.model_copy(update={"needs_search": False})
        return phase1, attempts
    raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                        "phase 1 : échec de validation après re-tentatives")


def _normalize_sources(output, source_set) -> None:
    """Rend les métadonnées des sources citées conformes à ce qui a été réellement récupéré.

    Les contrôles métier ont déjà vérifié l'ancrage ; cette étape garantit que ce qui parvient
    à l'étudiant (titre, revue, date, statut de vérification) vient de l'API, jamais du modèle.
    """
    if source_set is None:
        return
    for source in output.sources:
        record = source_set.by_id(source.source_id)
        if record is None:
            continue
        source.source = record.source
        source.title = record.title
        source.url = record.url
        source.doi = record.doi
        source.publication_date = record.publication_date
        source.access_date = record.access_date
        source.source_type = SourceType(record.source_type)
        source.verification_status = (VerificationStatus.verified if record.retrieved
                                      else VerificationStatus.not_verified)


def _produce_phase2(llm, system, request, annotations, sources_block, source_set, limits,
                    extra="", max_attempts=2):
    """Produit et valide (parser → schéma → métier → sécurité) la fiche finale."""
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            raw = problem_agent.phase2(llm, system, request, annotations, sources_block, extra)
            data = output_parser.extract_json(raw)
            output = schema_validation.validate(data)
        except PipelineError as exc:
            if attempts < max_attempts:
                extra = (f"Ta sortie précédente était invalide ({exc.state.value}). "
                         f"Détail : {exc.detail[:600]}\n"
                         "Réémets UNIQUEMENT un objet JSON conforme au schéma, sans texte autour.")
                continue
            raise
        violations = business_validation.validate_business(request, output, source_set)
        if violations:
            if attempts < max_attempts:
                extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                         + "\n".join(f"- {v}" for v in violations))
                continue
            raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                                "sortie non conforme : " + " ; ".join(violations))
        _normalize_sources(output, source_set)
        security_validation.check(output)
        return output, attempts
    raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                        "phase 2 : échec de validation après re-tentatives")


def analyze_problem(request: ProblemRequest, settings, llm, verifier_llm=None,
                    registry: Registry | None = None, fetcher: Fetcher | None = None,
                    cache: SourceCache | None = None) -> PipelineResult:
    from .input_controller import check_upstream

    verifier_llm = verifier_llm or llm
    # Remise a zero FACULTATIVE : le contrat d'un client reste `complete()`. Une doublure de
    # test n'a aucun etat a remettre, et lui en imposer un ferait porter au test une obligation
    # qui n'appartient qu'au client reel.
    if hasattr(llm, "nouvelle_campagne"):
        llm.nouvelle_campagne()

    input_validation.validate(request, settings.limits)
    check_upstream(request)

    annotations = security_layer.screen(request, settings.security)

    # Contexte de la recherche : déterministe et borné, jamais piloté par le LLM.
    source_set = SourceSet()
    if settings.sources.get("enabled", True):
        registry = registry or Registry(settings.providers_file)
        fetcher = fetcher or Fetcher(settings.sources, settings.limits,
                                     registry.allowed_hosts())
        cache = cache or SourceCache(settings.cache_db, settings.limits.cache_ttl_hours)

    phase1_attempts = 0
    phase1: Phase1Output | None = None

    if settings.sources.get("enabled", True):
        phase1, phase1_attempts = _produce_phase1(
            llm, problem_agent.load_phase1_system(), request, annotations, settings.limits)
        if phase1.search_intents:
            source_set = sources_stage.retrieve(phase1.search_intents, settings,
                                                registry=registry, fetcher=fetcher, cache=cache)
        annotations = security_layer.screen_sources(source_set, annotations)

    sources_block = source_set.to_prompt_block()
    output, attempts = _produce_phase2(
        llm, problem_agent.load_phase2_system(), request, annotations,
        sources_block, source_set, settings.limits)

    # Traçabilité garantie par la plateforme : les requêtes réellement exécutées, jamais
    # celles que le modèle prétendrait avoir utilisées.
    if source_set.queries:
        output.search_queries_used = list(source_set.queries)

    result = PipelineResult(
        output=output,
        source_set=source_set,
        phase1=phase1,
        attempts=phase1_attempts + attempts,
        injection_annotations=annotations,
        external_requests=fetcher.requests if fetcher else 0,
        cache_hits=cache.hits if cache else 0,
    )

    # Vérificateur indépendant — uniquement si l'agent se déclare prêt.
    if output.status == ProblemStatus.ready_for_verification:
        previous_corrections: set[str] | None = None
        reformulated = False
        for verification in range(1, settings.limits.max_verification_retries + 1):
            verdict = problem_verifier.verify(verifier_llm, request, output, source_set)
            result.verifier = verdict
            result.verifications = verification
            reformulated = False
            if verdict.verdict == VerifierVerdict.verified:
                output.validation.verified = True
                output.validation.verifier_status = "verified"
                result.verifier_status = "verified"
                break
            if verdict.verdict == VerifierVerdict.rejected:
                result.verifier_status = "rejected"
                break
            # Non-convergence : mêmes corrections redemandées deux fois → arrêt borné,
            # plutôt que de brûler des tours pour rien (SPEC §10.9).
            current = set(verdict.corrections)
            if previous_corrections is not None and current and current == previous_corrections:
                result.verifier_status = "verification_failed"
                break
            previous_corrections = current
            extra = ("Le vérificateur demande des corrections :\n"
                     + "\n".join(f"- {c}" for c in verdict.corrections))
            try:
                output, extra_attempts = _produce_phase2(
                    llm, problem_agent.load_phase2_system(), request, annotations,
                    sources_block, source_set, settings.limits, extra, max_attempts=2)
                result.attempts += extra_attempts
                if source_set.queries:
                    output.search_queries_used = list(source_set.queries)
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
            verdict = problem_verifier.verify(verifier_llm, request, output, source_set)
            result.verifier = verdict
            result.verifications += 1
            if verdict.verdict == VerifierVerdict.verified:
                output.validation.verified = True
                output.validation.verifier_status = "verified"
                result.verifier_status = "verified"
            else:
                result.verifier_status = "verification_failed"
    return result
