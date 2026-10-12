"""Orchestrateur de la problématisation (SPEC §9).

Enchaînement :
    pré-cadrage → chargement/indexation du corpus amont → LLM P1 (cartographie du problème)
      → LLM P2 (confrontation littéraire) → CONTRÔLE D'ANCRAGE
      → LLM P3 (identification/classification du gap) → GAP CHECK (déterministe, réseau borné)
      → LLM P4 (justification + note rédigée) → LLM P5 (question + objectifs candidats)
      → AMORCE D'ALIGNEMENT (déterministe) → bibliographie déterministe → validations
      → VÉRIFICATEUR indépendant.
Chaque étape est persistée (point de reprise) et bornée.
"""

from dataclasses import dataclass, field
import re
import unicodedata

from ..bibliography import render as render_reference
from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Confidence, Scope, SubjectReference
from ..schemas.output import (
    Bibliography,
    Evidence,
    ProblematizationOutput,
    ProblemStatus,
)
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from . import (
    alignment_stage,
    business_validation,
    confrontation_stage,
    corpus_loader,
    gap_check_stage,
    gap_stage,
    input_controller,
    input_validation,
    justification_stage,
    prerequisites,
    problem_mapping_stage,
    question_objectives_stage,
    security_layer,
    security_validation,
    verifier as verifier_module,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: ProblematizationOutput
    verifier: VerifierOutput | None = None
    verifier_status: str = "pending"
    attempts: int = 0
    verifications: int = 0
    injection_annotations: list = field(default_factory=list)
    external_requests: int = 0
    cache_hits: int = 0
    llm_calls: int = 0
    statements_removed: int = 0
    documents_read: int = 0
    stages: dict = field(default_factory=dict)

    @property
    def source_ids(self) -> list[str]:
        return sorted(self.output_corpus_ids)

    output_corpus_ids: list[str] = field(default_factory=list)


_PERIOD_RE = re.compile(r"\b((?:19|20)\d{2})\s*[-–—/]\s*((?:19|20)\d{2})\b")


def _alpha_key(text: str) -> str:
    """Clé de tri alphabétique insensible à la casse et aux accents (APA 7)."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _period(request) -> str:
    """Période couverte : champ d'entrée, sinon amont, sinon plage d'années explicite du sujet.

    Aucune invention : on ne retient que ce qui est DÉCLARÉ (champ, contexte amont) ou
    EXPLICITEMENT écrit dans le sujet (« 2020-2024 »).
    """
    explicit = str(getattr(request, "period", "") or "").strip()
    if explicit:
        return explicit
    for payload in (request.upstream_subject, request.upstream_problem):
        if payload is not None:
            value = str((payload.research_context or {}).get("temporal_scope", "") or "").strip()
            if value:
                return value
    match = _PERIOD_RE.search(request.subject_text or "")
    return f"{match.group(1)}-{match.group(2)}" if match else ""


def _reformulated_subject(request) -> str:
    """Reformulation du sujet DÉJÀ produite en amont. Jamais réécrite par cet agent."""
    for payload in (request.upstream_subject, request.upstream_problem):
        if payload is not None:
            container = payload.subject or payload.subject_reference or {}
            value = str(container.get("reformulated", "") or "").strip()
            if value:
                return value
    return ""


def _subject_reference(request) -> SubjectReference:
    return SubjectReference(original=request.subject_text,
                            reformulated=_reformulated_subject(request))


def _confidence(output) -> Confidence:
    """Confiance DÉTERMINÉE à partir des preuves mesurées (jamais auto-attribuée au hasard)."""
    written = output.evidence.statements_written or 0
    anchored = output.evidence.statements_anchored or 0
    total = output.evidence.documents_total or 0
    read = output.evidence.documents_read or 0
    anchor_ratio = (anchored / written) if written else 0.0
    coverage = (read / total) if total else 0.0
    overall = round(0.6 * anchor_ratio + 0.4 * coverage, 2)
    rationale = (f"ancrage verbatim : {anchored}/{written} affirmation(s) ({anchor_ratio:.0%}) ; "
                 f"texte intégral disponible pour {read}/{total} document(s) ({coverage:.0%})")
    return Confidence(overall=overall, rationale=rationale)


def _clarification_output(request, questions: list[str], notes: list[str]) -> ProblematizationOutput:
    return ProblematizationOutput(
        status=ProblemStatus.needs_clarification,
        subject_reference=_subject_reference(request),
        scope=_scope(request),
        clarification_questions=questions,
        limits_of_this_note=notes,
    )


def _scope(request) -> Scope:
    return Scope(discipline=request.discipline,
                 geographical_scope=request.geographical_scope or request.country,
                 population=request.population,
                 period=_period(request))


def _count_statements(output: ProblematizationOutput) -> tuple[int, int]:
    written = anchored = 0
    fields = [
        output.literature_confrontation.modeles_dominants,
        output.literature_confrontation.consensus,
        output.literature_confrontation.divergences,
        output.literature_confrontation.statements,
        output.gap.statements,
        output.justification.statements,
    ]
    for group in fields:
        for statement in group:
            written += 1
            if statement.anchored:
                anchored += 1
    return written, anchored


def run(request, settings, llm, verifier_llm=None, index=None, registry=None, fetcher=None,
        cache=None, allow_network: bool = True, persist=None) -> CampaignResult:
    verifier_llm = verifier_llm or llm
    # Remise a zero FACULTATIVE : le contrat d'un client reste `complete()`. Une doublure de
    # test n'a aucun etat a remettre, et lui en imposer un ferait porter au test une obligation
    # qui n'appartient qu'au client reel.
    if hasattr(llm, "nouvelle_campagne"):
        llm.nouvelle_campagne()
    stages: dict = {}

    input_validation.validate(request, settings.limits)
    input_controller.check_upstream(request)

    # Pré-cadrage : un cadre insuffisant (ou une revue non vérifiée) arrête tout AVANT tout LLM.
    pre = prerequisites.check(request)
    if pre["needs_clarification"]:
        output = _clarification_output(request, pre["questions"], pre["defaults_used"])
        return CampaignResult(output=output, stages={"prerequisites": pre})

    annotations = security_layer.screen(request, settings.security)

    # [5] chargement et indexation du corpus amont (déterministe)
    index = index or corpus_loader.load(request, settings.limits)
    annotations = security_layer.screen_corpus(index, annotations)
    stages["corpus"] = {
        "documents_total": len(index.documents),
        "documents_with_full_text": index.documents_with_full_text(),
    }

    if not index.documents:
        output = _clarification_output(
            request,
            ["Le corpus documentaire transmis est vide : pouvez-vous relancer l'étape 3 ou "
             "fournir les documents ?"],
            ["aucune affirmation ne peut être sourcée sans document"],
        )
        return CampaignResult(output=output, stages=stages)

    if not any(document.anchor_text().strip() for document in index.documents.values()):
        output = ProblematizationOutput(
            status=ProblemStatus.blocked,
            subject_reference=_subject_reference(request),
            scope=_scope(request),
            unknowns=["aucun texte exploitable (ni texte intégral, ni résumé) dans le corpus amont"],
            limits_of_this_note=[
                "aucun document du corpus amont ne contient de texte exploitable : l'ancrage "
                "verbatim est impossible, donc aucune affirmation ne peut être produite",
            ],
        )
        return CampaignResult(output=output, stages=stages)

    total_removed = 0
    attempts_total = 0

    def checkpoint(name: str, payload) -> None:
        if persist:
            persist(name, payload)

    # [6] P1 — cartographie du problème réel
    mapping, a1 = problem_mapping_stage.run(llm, request, annotations, index, settings.limits)
    attempts_total += a1
    checkpoint("problem_mapping", mapping)
    stages["problem_mapping"] = {"provenance": mapping.provenance.value}

    # [7-8] P2 — confrontation littéraire + ancrage
    confrontation, a2, removed2 = confrontation_stage.run(llm, request, annotations, index,
                                                         settings.limits)
    attempts_total += a2
    total_removed += removed2
    checkpoint("confrontation", confrontation)

    # [9] P3 — identification et classification du gap
    gap, a3, removed3 = gap_stage.run(llm, request, annotations, index, confrontation,
                                      settings.limits)
    attempts_total += a3
    total_removed += removed3

    # [10] gap check (déterministe, réseau borné)
    if allow_network:
        # Construits ICI (et non dans l'étage) pour que le bilan porte sur les requêtes
        # réellement effectuées : sinon `evidence.network_requests` restait à 0.
        if registry is None or fetcher is None or cache is None:
            from ..sources.cache import GapCheckCache
            from ..sources.http import ApiFetcher
            from ..sources.registry import Registry
            registry = registry or Registry(settings.providers_file)
            fetcher = fetcher or ApiFetcher(settings.sources or {}, settings.limits,
                                            registry.allowed_hosts())
            cache = cache or GapCheckCache(settings.cache_db, settings.limits.cache_ttl_hours)
        gap.gap_check = gap_check_stage.run(request, gap, settings, registry=registry,
                                            fetcher=fetcher, cache=cache)
    else:
        from ..schemas.gap import GapCheck, GapCheckResult
        gap.gap_check = GapCheck(result=GapCheckResult.unavailable,
                                 note="vérification réseau désactivée pour cette exécution")
    stages["gap"] = {"type": gap.type.value, "gap_check": gap.gap_check.result.value,
                     "publications": len(gap.gap_check.publications)}
    checkpoint("gap", gap)

    # [11] P4 — justification scientifique + note rédigée
    justification, a4, removed4 = justification_stage.run(llm, request, annotations, index,
                                                          confrontation, gap, settings.limits)
    attempts_total += a4
    total_removed += removed4
    checkpoint("justification", justification)

    # [12] P5 — question de recherche candidate + objectifs candidats
    question_output, a5 = question_objectives_stage.run(
        llm, request, annotations, index, gap, justification.problematique_note, settings.limits)
    attempts_total += a5

    # [13] amorce d'alignement (déterministe)
    alignment = alignment_stage.build(gap, request)

    def assemble() -> ProblematizationOutput:
        style = request.citation_style.value
        entries = []
        for doc_id in sorted(index.doc_ids):
            document = index.get(doc_id)
            if document is None:
                continue
            entries.append(render_reference(document, style))
        # APA 7 : liste bibliographique ALPHABÉTIQUE et sans préfixe « [Dx] » (les identifiants
        # restent portés par le corps de la note et par evidence/source_ids).
        entries.sort(key=_alpha_key)
        output = ProblematizationOutput(
            status=ProblemStatus.ready_for_verification,
            subject_reference=_subject_reference(request),
            scope=_scope(request),
            problem_mapping=mapping,
            literature_confrontation=confrontation,
            gap=gap,
            justification=justification.justification,
            problematique_note=justification.problematique_note,
            research_question=question_output.research_question,
            objectives=question_output.objectives,
            methodological_alignment=alignment,
            bibliography=Bibliography(style=style, entries=entries, entries_count=len(entries)),
            limits_of_this_note=[],
        )
        written, anchored = _count_statements(output)
        output.evidence = Evidence(
            statements_written=written,
            statements_anchored=anchored,
            statements_removed=total_removed,
            documents_read=index.documents_with_full_text(),
            documents_total=len(index.documents),
            llm_calls=llm.calls,
            network_requests=getattr(fetcher, "requests", 0) if fetcher else 0,
        )
        return output


    out = assemble()

    # Limites déclarées (honnêteté)
    limits_notes: list[str] = []
    if total_removed:
        limits_notes.append(
            f"{total_removed} affirmation(s) retirée(s) : citation introuvable dans le texte réel "
            "du document cité (ancrage verbatim obligatoire)")
    not_read = [d.doc_id for d in index.documents.values() if d.scope != "full_text"]
    if not_read:
        limits_notes.append(
            f"{len(not_read)} document(s) sans texte intégral disponible : les affirmations ne "
            "peuvent s'appuyer que sur le résumé ou les extraits déjà vérifiés (portée déclarée)")
    if gap.gap_check.result.value == "unavailable":
        limits_notes.append(
            "le gap n'a pas pu être vérifié automatiquement (sources indisponibles) : cela ne "
            "confirme ni n'infirme sa réalité")
    elif gap.gap_check.result.value == "already_addressed":
        limits_notes.append(
            f"{len(gap.gap_check.publications)} publication(s) proche(s) du gap ont été trouvées : "
            "le gap pourrait être partiellement comblé — à examiner par l'étudiant")
    # Gap check partiellement empêché : ce qui n'a pas pu être vérifié doit être DIT (le
    # « not_found » ne vaut que pour les sources réellement interrogées).
    if gap.gap_check.providers_failed:
        failed = ", ".join(sorted({str(f.get("provider", "")) for f in gap.gap_check.providers_failed
                                   if f.get("provider")})) or "fournisseur(s) inconnu(s)"
        limits_notes.append(
            f"la vérification automatique du gap n'a pas abouti ({len(gap.gap_check.providers_failed)} "
            f"échec(s) de fournisseur : {failed}) : l'absence de travaux proches n'est PAS établie, "
            "seulement non détectée dans les sources interrogées")
        out.unknowns.append(
            "l'absence de littérature proche du gap n'est pas prouvée : la vérification "
            f"documentaire est incomplète ({failed} indisponible(s) au moment du test)")
    if alignment.upstream_coherence.value == "divergent":
        limits_notes.append("amorce d'alignement divergente du diagnostic de l'étape 3 (déclarée)")
    if alignment.upstream_coherence.value == "absent":
        limits_notes.append("aucun diagnostic méthodologique d'amont transmis pour comparaison")
    limits_notes.extend(pre["defaults_used"])
    out.limits_of_this_note = limits_notes

    # Si RIEN n'a pu être ancré, la production n'est pas sourçable : on le dit plutôt que de
    # transmettre au vérificateur une note sans fondement (garde anti-hallucination).
    if out.evidence.statements_anchored == 0:
        out.status = ProblemStatus.blocked
        out.unknowns.append(
            "aucune affirmation n'a pu être ancrée dans le texte réel des documents amont : "
            "la problématique ne peut pas être sourcée en l'état")
        out.limits_of_this_note.append(
            "toutes les affirmations produites ont été retirées faute de citation présente dans "
            "le texte réellement disponible (ancrage verbatim obligatoire)")

    # Confiance : dérivée des preuves mesurées (jamais laissée vide ni auto-attribuée au hasard).
    out.confidence = _confidence(out)

    # [14] validations finales
    violations = business_validation.validate_semantics(out, request, index)
    violations += business_validation.validate_final(out)
    if violations:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(violations[:8]))
    security_validation.check_payload(out)
    checkpoint("problematique_output", out)

    result = CampaignResult(
        output=out,
        attempts=attempts_total,
        injection_annotations=annotations,
        external_requests=getattr(fetcher, "requests", 0) if fetcher else 0,
        cache_hits=getattr(cache, "hits", 0) if cache else 0,
        llm_calls=llm.calls,
        statements_removed=total_removed,
        documents_read=index.documents_with_full_text(),
        stages=stages,
        output_corpus_ids=sorted(index.doc_ids),
    )

    # [15] vérificateur indépendant
    if out.status == ProblemStatus.ready_for_verification:
        previous: set[str] | None = None
        reformulated = False
        for verification in range(1, settings.limits.max_verification_retries + 1):
            verdict = verifier_module.verify(verifier_llm, request, out, index)
            result.verifier = verdict
            result.verifications = verification
            reformulated = False
            if verdict.verdict == VerifierVerdict.verified:
                out.validation.verified = True
                out.validation.verifier_status = "verified"
                result.verifier_status = "verified"
                break
            if verdict.verdict == VerifierVerdict.rejected:
                result.verifier_status = "rejected"
                break
            current = set(verdict.corrections)
            if previous is not None and current and current == previous:
                result.verifier_status = "verification_failed"
                break
            previous = current
            extra = ("Le vérificateur demande des corrections :\n"
                     + "\n".join(f"- {c}" for c in verdict.corrections))
            try:
                justification, a4b, removed4b = justification_stage.run(
                    llm, request, annotations, index, confrontation, gap, settings.limits, extra)
                question_output, a5b = question_objectives_stage.run(
                    llm, request, annotations, index, gap, justification.problematique_note,
                    settings.limits, extra)
                total_removed += removed4b
                result.attempts += a4b + a5b
                out.justification = justification.justification
                out.problematique_note = justification.problematique_note
                out.research_question = question_output.research_question
                out.objectives = question_output.objectives
                written, anchored = _count_statements(out)
                out.evidence.statements_written = written
                out.evidence.statements_anchored = anchored
                out.evidence.statements_removed = total_removed
                result.statements_removed = total_removed
                result.output = out
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
            verdict = verifier_module.verify(verifier_llm, request, out, index)
            result.verifier = verdict
            result.verifications += 1
            if verdict.verdict == VerifierVerdict.verified:
                out.validation.verified = True
                out.validation.verifier_status = "verified"
                result.verifier_status = "verified"
            else:
                result.verifier_status = "verification_failed"

    checkpoint("problematique_output", out)
    return result
