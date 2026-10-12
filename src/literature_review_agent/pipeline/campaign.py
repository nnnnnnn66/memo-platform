"""Orchestrateur de la campagne documentaire (SPEC §9).

Enchaînement :
    pré-cadrage → LLM P1 (mots-clés/stratégie) → recherche documentaire déterministe
      → acquisition et lecture du texte intégral → LLM P2 (notation/extraction par lots)
      → sélection du corpus → LLM P3 (comparaison + synthèse) → LLM P4 (diagnostic)
      → bibliographie déterministe → validations → VÉRIFICATEUR indépendant.
Chaque étape est persistée (point de reprise) et bornée.
"""

from dataclasses import dataclass, field

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..schemas.common import Scope, SubjectReference
from ..schemas.document import (
    DocumentRecord,
    FullTextInfo,
    GeographicScope,
    SourceType,
    VerificationStatus,
)
from ..schemas.output import (
    Bibliography,
    Corpus as CorpusView,
    ReviewOutput,
    ReviewStatus,
)
from ..schemas.verifier import VerifierOutput, VerifierVerdict
from ..sources.cache import DocumentCache
from ..sources.corpus import Corpus, detect_geography, normalize_language
from ..sources.fulltext import FullTextStore, is_quote_anchored
from ..sources.http import ApiFetcher, FileDownloader
from ..sources.registry import Registry
from ..bibliography import styles
from . import (
    business_validation,
    diagnosis_stage,
    fulltext_stage,
    keywords_stage,
    prerequisites,
    retrieval_stage,
    scoring_stage,
    security_layer,
    security_validation,
    synthesis_stage,
    verifier as verifier_module,
)

log = get_logger("pipeline.campaign")


@dataclass
class CampaignResult:
    output: ReviewOutput
    verifier: VerifierOutput | None = None
    verifier_status: str = "pending"
    attempts: int = 0
    verifications: int = 0
    injection_annotations: list = field(default_factory=list)
    external_requests: int = 0
    cache_hits: int = 0
    llm_calls: int = 0
    documents: dict = field(default_factory=dict)
    dropped_claims: int = 0
    stages: dict = field(default_factory=dict)

    @property
    def source_ids(self) -> list[str]:
        return [doc.doc_id for doc in self.output.corpus.documents]

    @property
    def downloaded_count(self) -> int:
        return sum(1 for entry in self.documents.values() if entry["info"]["downloaded"])


def _clarification_output(request, questions: list[str], limits_notes: list[str]) -> ReviewOutput:
    return ReviewOutput(
        status=ReviewStatus.needs_clarification,
        subject_reference=SubjectReference(original=request.subject_text),
        scope=Scope(discipline=request.discipline,
                    geographical_scope=request.geographical_scope or request.country,
                    period=request.period, languages=list(request.languages)),
        clarification_questions=questions,
        limits_of_this_review=limits_notes,
    )


def _to_document_record(record, documents: dict, style: str) -> DocumentRecord:
    info = (documents.get(record.doc_id) or {}).get("info") or {}
    geographic, evidence = detect_geography(f"{record.title} {record.abstract}")
    document = DocumentRecord(
        doc_id=record.doc_id,
        provider=record.provider,
        source_type=SourceType(record.source_type),
        document_type=record.document_type,
        authors=record.authors,
        title=record.title,
        year=record.year,
        venue=record.venue,
        doi=record.doi,
        url=record.url,
        volume=record.volume,
        issue=record.issue,
        pages=record.pages,
        language=normalize_language(record.language),
        abstract=record.abstract,
        geographic_scope=GeographicScope(geographic),
        geographic_evidence=evidence,
        relevance=record.relevance,
        theme=record.theme,
        extraction_scope=record.extraction_scope,
        method=record.method,
        field_site=record.field_site,
        findings=record.findings,
        limits=record.limits,
        full_text=FullTextInfo(
            available=bool(info.get("available")),
            downloaded=bool(info.get("downloaded")),
            file_name=info.get("file_name", ""),
            file_path=info.get("file_path", ""),
            sha256=info.get("sha256", ""),
            bytes=int(info.get("bytes") or 0),
            pages=int(info.get("pages") or 0),
            text_chars=int(info.get("text_chars") or 0),
            text_layer=bool(info.get("text_layer", False)),
            source_url=info.get("source_url", ""),
            license=info.get("license", ""),
            extraction_tool=info.get("extraction_tool", ""),
            download_error=info.get("download_error", ""),
        ),
        retrieved=True,
        verification_status=VerificationStatus.verified,
    )
    document.reference = styles.render(document, style)
    return document


def sanitize_claims(records, source_texts: dict, abstracts: dict) -> tuple[int, list[str]]:
    """Retire les affirmations dont la citation n'existe pas dans le texte réellement lu.

    Une citation introuvable est une citation non vérifiable : elle est retirée (jamais conservée
    « au bénéfice du doute ») et l'opération est signalée dans les limites de la revue.
    """
    dropped = 0
    notes: list[str] = []
    for record in records:
        text = source_texts.get(record.doc_id, "")
        abstract = abstracts.get(record.doc_id, "")
        kept_findings, kept_limits = [], []
        for claim in list(record.findings or []):
            quote = (claim.get("quote") if isinstance(claim, dict) else claim.quote) or ""
            if quote and (is_quote_anchored(quote, text) or is_quote_anchored(quote, abstract)):
                kept_findings.append(claim)
            else:
                dropped += 1
        for claim in list(record.limits or []):
            quote = (claim.get("quote") if isinstance(claim, dict) else claim.quote) or ""
            if quote and (is_quote_anchored(quote, text) or is_quote_anchored(quote, abstract)):
                kept_limits.append(claim)
            else:
                dropped += 1
        record.findings = kept_findings
        record.limits = kept_limits
    if dropped:
        notes.append(
            f"{dropped} affirmation(s) retirée(s) : citation introuvable dans le texte réellement "
            "lu (ancrage verbatim obligatoire)"
        )
    return dropped, notes


def run(request, settings, llm, verifier_llm=None, registry: Registry | None = None,
        fetcher: ApiFetcher | None = None, cache: DocumentCache | None = None,
        downloader: FileDownloader | None = None, store: FullTextStore | None = None,
        persist=None) -> CampaignResult:
    from . import input_controller, input_validation

    verifier_llm = verifier_llm or llm
    # Remise a zero FACULTATIVE : le contrat d'un client reste `complete()`. Une doublure de
    # test n'a aucun etat a remettre, et lui en imposer un ferait porter au test une obligation
    # qui n'appartient qu'au client reel.
    if hasattr(llm, "nouvelle_campagne"):
        llm.nouvelle_campagne()
    stages: dict = {}

    input_validation.validate(request, settings.limits)
    input_controller.check_upstream(request)

    # [4] pré-cadrage : un cadre insuffisant arrête tout AVANT toute requête réseau.
    pre = prerequisites.check(request)
    if pre["needs_clarification"]:
        output = _clarification_output(request, pre["questions"], pre["defaults_used"])
        return CampaignResult(output=output, stages={"prerequisites": pre})

    annotations = security_layer.screen(request, settings.security)

    registry = registry or Registry(settings.providers_file)
    fetcher = fetcher or ApiFetcher(settings.sources, settings.limits, registry.allowed_hosts())
    cache = cache or DocumentCache(settings.cache_db, settings.limits.cache_ttl_hours)
    downloader = downloader or FileDownloader(settings.sources, settings.fulltext, settings.limits)
    session_path = (settings.workspace_dir / request.student_id / (request.session_id or "session"))
    store = store or FullTextStore(session_path, settings.limits.max_text_chars_per_doc)

    def checkpoint(name: str, payload) -> None:
        if persist:
            persist(name, payload)

    # [5-6] phase 1 : concepts, mots-clés, stratégie
    keywords, kw_attempts = keywords_stage.run(llm, request, annotations, settings.limits)
    stages["keywords"] = {
        "concepts": [c.concept for c in keywords.concepts],
        "queries": [q.query for q in keywords.queries],
        "too_broad": keywords.subject_is_too_broad,
        "strategy": keywords.strategy.model_dump(mode="json"),
    }
    checkpoint("keywords", keywords)
    if keywords.subject_is_too_broad:
        output = _clarification_output(request, keywords.clarification_questions,
                                       ["sujet jugé trop vaste : délimitation demandée avant "
                                        "toute campagne documentaire"])
        output.keywords = keywords.model_dump(mode="json")
        return CampaignResult(output=output, attempts=kw_attempts, stages=stages)

    # [7-8] recherche documentaire déterministe
    concept_terms: list[str] = []
    for concept in keywords.concepts:
        concept_terms.extend([concept.concept, *concept.keywords_fr, *concept.keywords_en,
                              *concept.synonyms, *concept.variants])
    corpus = retrieval_stage.run_campaign(keywords.queries, settings, registry=registry,
                                          fetcher=fetcher, cache=cache,
                                          concept_terms=concept_terms)
    corpus.queries = [q for q in corpus.queries]
    annotations = security_layer.screen_corpus(corpus, annotations)
    checkpoint("corpus", {"records": [r.to_dict() for r in corpus.records],
                          "providers_used": corpus.providers_used,
                          "providers_failed": corpus.providers_failed,
                          "duplicates_removed": corpus.duplicates_removed,
                          "queries": corpus.queries})
    stages["retrieval"] = {"documents_collected": len(corpus),
                           "duplicates_removed": corpus.duplicates_removed,
                           "providers_used": corpus.providers_used,
                           "queries": corpus.queries}

    # [9bis] acquisition et lecture du texte intégral
    documents = fulltext_stage.acquire(corpus, settings, store, registry, fetcher, downloader)
    annotations = security_layer.screen_documents(documents, annotations)
    source_texts = {doc_id: fulltext_stage.document_text(store, documents, doc_id)
                    for doc_id in documents}
    abstracts = {r.doc_id: r.abstract for r in corpus.records}
    for record in corpus.records:
        record.full_text = (documents.get(record.doc_id) or {}).get("info") or {}
    checkpoint("documents", {doc_id: {"info": entry["info"], "text_file": entry["text_file"]}
                             for doc_id, entry in documents.items()})
    stages["fulltext"] = {"attempted": len(documents),
                          "downloaded": downloader.downloads,
                          "megabytes": round(downloader.bytes_downloaded / 1e6, 1)}

    # [10] phase 2 : notation/extraction par lots
    analyses, scoring_attempts = scoring_stage.run(llm, request, corpus, documents, annotations,
                                                   settings)
    scoring_stage.apply_analyses(corpus, analyses)
    checkpoint("analysis", analyses)

    # Correction déterministe de portée : un document annoncé « texte intégral » alors qu'aucun
    # texte n'a été réellement lu est ramené à « résumé » (et à « métadonnées » sans résumé, auquel
    # cas les affirmations extraites sont retirées). Le modèle ne peut pas surestimer sa portée.
    scope_corrected = 0
    for record in corpus.records:
        if record.extraction_scope != "full_text":
            continue
        read = bool(record.full_text.get("downloaded")) and bool(record.full_text.get("text_layer"))
        if read:
            continue
        scope_corrected += 1
        if record.abstract:
            record.extraction_scope = "abstract_only"
        else:
            record.extraction_scope = "metadata_only"
            record.findings = []
            record.limits = []
    if scope_corrected:
        log.info("portée d'extraction corrigée pour %s document(s) non lus", scope_corrected)

    # [11] sélection finale : seuls les documents réellement analysés ET jugés pertinents sont
    # retenus. Les écarts sont comptés et déclarés (le corpus n'est jamais gonflé).
    retained, sufficiency, selection_stats = scoring_stage.select_corpus(
        corpus, settings.limits, analyses)
    stages["selection"] = {"retained": len(retained), "sufficiency": sufficiency,
                           **selection_stats}
    if not retained:
        details = []
        if selection_stats["not_analysed_over_budget"]:
            details.append(f"{selection_stats['not_analysed_over_budget']} document(s) non analysés "
                           "faute de budget d'analyse")
        if selection_stats["rejected_low_relevance"]:
            details.append(f"{selection_stats['rejected_low_relevance']} document(s) écartés par le "
                           "seuil de pertinence")
        if selection_stats["rejected_no_concept_match"]:
            details.append(f"{selection_stats['rejected_no_concept_match']} document(s) sans "
                           "recoupement avec les concepts du sujet")
        output = ReviewOutput(
            status=ReviewStatus.blocked,
            subject_reference=SubjectReference(original=request.subject_text),
            scope=Scope(discipline=request.discipline,
                        geographical_scope=request.geographical_scope or request.country,
                        period=request.period, languages=list(request.languages)),
            keywords=keywords.model_dump(mode="json"),
            unknowns=["aucun document pertinent n'a pu être retenu auprès des fournisseurs "
                      "déclarés"],
            limits_of_this_review=[
                "les fournisseurs configurés n'ont renvoyé aucun document exploitable pour ces "
                "requêtes",
                "les échecs déclarés sont listés dans le corpus",
                *details,
            ],
        )
        return CampaignResult(output=output, attempts=kw_attempts + scoring_attempts,
                              external_requests=fetcher.requests, cache_hits=cache.hits,
                              llm_calls=llm.calls, documents=documents, stages=stages)

    # [12-13] comparaison et synthèse
    synthesis, syn_attempts = synthesis_stage.run(llm, request, retained, annotations,
                                                 settings.limits)

    # [14] diagnostic méthodologique
    diagnosis, diag_attempts = diagnosis_stage.run(llm, request, synthesis, retained, annotations,
                                                   settings)
    checkpoint("synthesis", synthesis)
    checkpoint("diagnosis", diagnosis)

    # Citations non vérifiables retirées AVANT l'assemblage final
    dropped, drop_notes = sanitize_claims(retained, source_texts, abstracts)

    # [13bis] bibliographie déterministe
    style = request.citation_style.value if hasattr(request.citation_style, "value") \
        else str(request.citation_style)
    document_records = [_to_document_record(r, documents, style) for r in retained]
    entries = [doc.reference for doc in document_records if doc.reference]

    counts = corpus.counts(retained)
    by_geography: dict[str, int] = {}
    for record in retained:
        scope, _ = detect_geography(f"{record.title} {record.abstract}")
        by_geography[scope] = by_geography.get(scope, 0) + 1

    limits_notes = list(synthesis.limits_of_this_review) + drop_notes
    if sufficiency != "sufficient":
        limits_notes.append(
            f"corpus_sufficiency = {sufficiency} : {len(retained)} documents retenus pour un "
            f"objectif de couverture configuré de {settings.limits.max_documents} documents"
        )
    not_read = [doc.doc_id for doc in document_records if not doc.full_text.downloaded]
    if not_read:
        limits_notes.append(
            f"{len(not_read)} document(s) sans texte intégral téléchargé (accès fermé ou "
            "téléchargement refusé) : l'analyse repose alors sur le résumé"
        )
    if pre["defaults_used"]:
        limits_notes.extend(pre["defaults_used"])
    # Filtres de pertinence appliqués : déclarés pour que l'étudiant sache ce qui a été écarté.
    if selection_stats["rejected_low_relevance"] or selection_stats["rejected_no_concept_match"]:
        limits_notes.append(
            f"{selection_stats['rejected_low_relevance']} document(s) écarté(s) sous le seuil de "
            f"pertinence et {selection_stats['rejected_no_concept_match']} sans recoupement avec "
            "les concepts du sujet : ils ne figurent pas dans la revue"
        )
    if selection_stats["not_analysed_over_budget"]:
        limits_notes.append(
            f"{selection_stats['not_analysed_over_budget']} document(s) collectés n'ont pas été "
            "analysés (budget d'analyse borné) et ne sont donc pas retenus"
        )
    if selection_stats.get("not_retained_over_max"):
        limits_notes.append(
            f"{selection_stats['not_retained_over_max']} document(s) pertinent(s) n'ont pas été "
            f"retenus : plafond du corpus atteint ({settings.limits.max_documents})"
        )
    if selection_stats.get("rejected_duplicate_title"):
        limits_notes.append(
            f"{selection_stats['rejected_duplicate_title']} document(s) au titre identique à un "
            "document déjà retenu (même travail vu par deux fournisseurs, DOI distincts) ont été "
            "écartés du corpus pour éviter les doublons"
        )
    if scope_corrected:
        limits_notes.append(
            f"{scope_corrected} document(s) annoncé(s) en texte intégral par le modèle sans texte "
            "réellement lu : portée ramenée à « résumé » (garde anti-surévaluation)"
        )
    if corpus.providers_failed:
        limits_notes.append(
            f"{len(corpus.providers_failed)} échec(s) de fournisseur déclaré(s) : "
            + ", ".join(sorted({f['provider'] for f in corpus.providers_failed}))
        )

    output = ReviewOutput(
        status=ReviewStatus.ready_for_verification,
        subject_reference=SubjectReference(original=request.subject_text,
                                           reformulated=keywords.subject_reference.reformulated),
        scope=Scope(discipline=request.discipline,
                    geographical_scope=request.geographical_scope or request.country,
                    period=request.period, languages=list(request.languages),
                    cascade=settings.sources.get("cascade", [])),
        keywords=keywords.model_dump(mode="json"),
        corpus=CorpusView(
            documents=document_records,
            documents_count=len(document_records),
            corpus_sufficiency=sufficiency,
            duplicates_removed=corpus.duplicates_removed,
            providers_used=corpus.providers_used,
            providers_failed=corpus.providers_failed,
            queries=corpus.queries,
            by_language=counts["by_language"],
            by_geography=by_geography,
            by_type=counts["by_type"],
            full_text_downloaded=sum(1 for d in document_records if d.full_text.downloaded),
        ),
        comparison=synthesis.comparison,
        synthesis=synthesis.synthesis,
        diagnosis=diagnosis,
        bibliography=Bibliography(style=style, entries=entries, entries_count=len(entries)),
        unknowns=synthesis.unknowns,
        limits_of_this_review=limits_notes,
    )

    # [15] validations finales
    violations = business_validation.validate_semantics(
        output, request, source_texts, abstracts,
        sufficiency_expected=sufficiency,
        min_useful=settings.limits.min_documents_useful)
    violations += business_validation.validate_final(output)
    if violations:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                            "sortie non conforme : " + " ; ".join(violations[:8]))
    security_validation.check_payload(output)

    result = CampaignResult(
        output=output,
        attempts=kw_attempts + scoring_attempts + syn_attempts + diag_attempts,
        injection_annotations=annotations,
        external_requests=fetcher.requests,
        cache_hits=cache.hits,
        llm_calls=llm.calls,
        documents=documents,
        dropped_claims=dropped,
        stages=stages,
    )

    # [16] vérificateur indépendant
    if output.status == ReviewStatus.ready_for_verification:
        previous: set[str] | None = None
        reformulated = False
        for verification in range(1, settings.limits.max_verification_retries + 1):
            verdict = verifier_module.verify(verifier_llm, request, output, retained)
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
            current = set(verdict.corrections)
            if previous is not None and current and current == previous:
                result.verifier_status = "verification_failed"
                break
            previous = current
            extra = ("Le vérificateur demande des corrections :\n"
                     + "\n".join(f"- {c}" for c in verdict.corrections))
            try:
                synthesis, extra_attempts = synthesis_stage.run(
                    llm, request, retained, annotations, settings.limits, extra)
                diagnosis, diag2 = diagnosis_stage.run(llm, request, synthesis, retained,
                                                       annotations, settings, extra)
                result.attempts += extra_attempts + diag2
                output.comparison = synthesis.comparison
                output.synthesis = synthesis.synthesis
                output.diagnosis = diagnosis
                output.unknowns = synthesis.unknowns
                result.output = output
                result.verifier_status = "corrections_requested"
                reformulated = True
            except PipelineError:
                result.verifier_status = "verification_failed"
                break
        else:
            result.verifier_status = "verification_failed"

        # La DERNIÈRE reformulation n'était jamais jugée : la boucle s'arrêtait sur
        # `verification_failed` alors que la version corrigée peut parfaitement passer (vérifié en
        # rejouant le vérificateur seul sur la sortie finale — verdict `verified`). Une vérification
        # finale tranche, sans nouvelle reformulation (le budget de re-tentatives reste borné).
        if reformulated:
            verdict = verifier_module.verify(verifier_llm, request, output, retained)
            result.verifier = verdict
            result.verifications += 1
            if verdict.verdict == VerifierVerdict.verified:
                output.validation.verified = True
                output.validation.verifier_status = "verified"
                result.verifier_status = "verified"
            else:
                result.verifier_status = "verification_failed"

    checkpoint("review_output", output)
    return result
