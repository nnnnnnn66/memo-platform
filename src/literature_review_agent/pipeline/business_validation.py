"""Validation métier de la sortie : ancrage, honnêteté, anti-fusion, cohérence de matrice.

Contrôles déterministes. Le plus important : **chaque citation doit exister littéralement** dans
le texte réellement lu (ou dans le résumé quand le texte intégral n'a pas été obtenu). Une
affirmation inventée ne peut pas franchir cette barrière.
"""

import re

from ..diagnosis import matrix
from ..schemas.output import CorpusSufficiency, ReviewOutput, ReviewStatus

FORBIDDEN_MARKERS = [
    "problématique",
    "question de recherche",
    "question principale",
    "hypothèse de recherche",
    "hypothèses de recherche",
    "objectifs de recherche",
    "plan de mémoire",
]

# R2 — anti-fusion. Un test de SOUS-CHAÎNE brut déclenchait de fausses alertes qui refusaient la
# campagne entière : « la question reste problématique », « la problématique de la mesure de la
# productivité » sont des tournures normales dans une revue de littérature en français (constaté en
# exécution réelle : `R2: fusion interdite détectée (marqueur « problématique »)` sur une synthèse
# par ailleurs vérifiée). Le signalement n'est donc déclenché que sur un indice de PRODUCTION ou
# d'APPROPRIATION ; le jugement de fond reste au vérificateur indépendant (contrôle L10).
_DET = r"(?:la|le|les|l['’]|une?|cette|ce|ces)"
_FUSION_PATTERNS = [
    # 1. marqueur en tête de ligne (titre de section, puce, numérotation)
    r"(?im)^[ \t]*(?:[-*+>#]|\d+[.)])?[ \t]*(?:\*\*|__)?[ \t]*{m}\b",
    # 2. appropriation explicite
    r"\b(?:notre|nos|ma|mon|mes)[ \t]+{m}\b",
    # 3. « la problématique de ce mémoire »
    r"\b{det}[ \t]+{m}[ \t]+(?:de|du|des|d['’])[ \t]+"
    r"(?:ce|cet|cette|ces|la présente|mon|ma|notre)[ \t]*(?:mémoire|recherche|étude|thèse|travail|revue)",
    # 4. élément annoncé comme PRODUIT (« la problématique retenue », « les hypothèses suivantes »)
    r"\b{det}[ \t]+{m}\b[^.!?]{{0,40}}\b"
    r"(?:retenue?s?|proposée?s?|formulée?s?|principale?s?|suivante?s?|émise?s?)\b",
    # 5. verbe de production portant sur l'élément
    r"\b(?:nous|je)[ \t]+(?:proposons|formulons|retenons|définissons|posons|avançons)\b"
    r"[^.]{{0,60}}\b{m}\b",
]


def fusion_markers(text: str) -> list[str]:
    """Marqueurs de fusion RÉELLEMENT produits (et non une simple occurrence du mot)."""
    lowered = (text or "").lower()
    found: list[str] = []
    for marker in FORBIDDEN_MARKERS:
        escaped = re.escape(marker)
        patterns = [pattern.format(m=escaped, det=_DET) for pattern in _FUSION_PATTERNS]
        if any(re.search(pattern, lowered) for pattern in patterns):
            found.append(marker)
    return found

_CORPUS_FIELDS = ("convergences", "divergences", "limits", "gaps")


def _free_texts(output: ReviewOutput) -> str:
    parts = [output.synthesis.state_of_knowledge, output.diagnosis.justification]
    parts.extend(output.synthesis.open_questions)
    parts.extend(output.synthesis.blind_spots)
    parts.extend(output.synthesis.caution_notes)
    for theme in output.comparison.themes:
        for field in _CORPUS_FIELDS:
            parts.extend(getattr(theme, field))
    return " ".join(parts)


def validate_semantics(output: ReviewOutput, request, source_texts: dict,
                       abstracts: dict, sufficiency_expected: str | None = None,
                       min_useful: int = 10) -> list[str]:
    """Contrôles sur le contenu produit (ancrage, doc_id, fusion, bibliographie)."""
    violations: list[str] = []
    by_id = output.documents_by_id()
    known_ids = set(by_id)

    # R1 — fidélité du sujet
    if output.subject_reference.original.strip() != request.subject_text.strip():
        violations.append("R1: subject_reference.original ne correspond pas au sujet reçu")

    # R2 — anti-fusion : aucune production de l'étape suivante
    for marker in fusion_markers(_free_texts(output)):
        violations.append(f"R2: fusion interdite détectée (marqueur « {marker} »)")

    # R3 — tous les doc_id cités existent dans le corpus retenu
    cited: set[str] = set()
    for theme in output.comparison.themes:
        cited |= set(theme.doc_ids)
    unknown = cited - known_ids
    if unknown:
        violations.append(f"R3: doc_id cités hors corpus : {sorted(unknown)}")
    if output.status == ReviewStatus.ready_for_verification and not cited:
        violations.append("R3: comparaison sans aucun document cité")

    # R4 — cohérence des compteurs
    if output.corpus.documents_count != len(output.corpus.documents):
        violations.append(
            f"R4: documents_count ({output.corpus.documents_count}) ≠ nombre réel de documents "
            f"({len(output.corpus.documents)})"
        )
    if output.bibliography.entries_count != len(output.corpus.documents):
        violations.append(
            f"R4: bibliographie ({output.bibliography.entries_count}) ≠ corpus "
            f"({len(output.corpus.documents)})"
        )

    # R5 — ancrage verbatim des citations (cœur de l'anti-hallucination)
    for record in output.corpus.documents:
        source_text = source_texts.get(record.doc_id, "")
        abstract = abstracts.get(record.doc_id, "")
        for claim in list(record.findings) + list(record.limits):
            quote = (claim.quote or "").strip()
            if not quote:
                violations.append(f"R5: {record.doc_id} : affirmation sans citation")
                continue
            if len(quote) < 25:
                violations.append(f"R5: {record.doc_id} : citation trop courte ({len(quote)} car.)")
                continue
            anchor_text = source_text or abstract
            if not anchor_text:
                violations.append(
                    f"R5: {record.doc_id} : citation fournie alors qu'aucun texte n'est disponible"
                )
                continue
            if not _anchored(quote, source_text, abstract):
                violations.append(
                    f"R5: {record.doc_id} : citation introuvable dans le texte réellement lu "
                    f"(« {quote[:60]}… »)"
                )

    # R6 — extraction_scope cohérent avec l'état réel du document
    for record in output.corpus.documents:
        read = record.full_text.downloaded and record.full_text.text_layer
        if record.extraction_scope.value == "full_text" and not read:
            violations.append(
                f"R6: {record.doc_id} déclarée « full_text » alors que le texte intégral n'est pas "
                "disponible"
            )
        if record.findings and record.extraction_scope.value == "metadata_only":
            violations.append(
                f"R6: {record.doc_id} présente des résultats avec une extraction "
                "« metadata_only »"
            )

    # R7 — dédoublonnage effectif
    seen_doi: set[str] = set()
    seen_title: set[str] = set()
    for record in output.corpus.documents:
        doi = (record.doi or "").lower()
        if doi and doi in seen_doi:
            violations.append(f"R7: DOI en double dans le corpus retenu : {record.doi}")
        seen_doi.add(doi)
        title = " ".join((record.title or "").lower().split())
        if title and title in seen_title:
            violations.append(f"R7: titre en double dans le corpus retenu : {record.title[:60]}")
        seen_title.add(title)

    # R8 — cohérence du diagnostic avec la matrice
    if output.diagnosis.matrix_row_id not in matrix.BY_ID:
        violations.append(f"R8: matrix_row_id inconnu : {output.diagnosis.matrix_row_id!r}")
    else:
        issues = matrix.row_coherence_issues(
            output.diagnosis.matrix_row_id,
            output.diagnosis.reasoning_logic.value,
            output.diagnosis.research_type.value,
            output.diagnosis.approach.value,
            output.diagnosis.techniques,
        )
        if issues and not output.diagnosis.alignment_alerts:
            violations.append("R8: incohérence de matrice non signalée : " + " ; ".join(issues))

    # R9 — honnêteté sur la suffisance du corpus
    declared = output.corpus.corpus_sufficiency
    declared_value = getattr(declared, "value", str(declared))
    if sufficiency_expected is not None:
        expected = (sufficiency_expected.value
                    if hasattr(sufficiency_expected, "value") else str(sufficiency_expected))
        if declared_value != expected:
            violations.append(
                f"R9: corpus_sufficiency déclaré « {declared_value} » alors que le calcul "
                f"déterministe donne « {expected} »")
    elif declared == CorpusSufficiency.sufficient and len(output.corpus.documents) < min_useful:
        violations.append(
            f"R9: corpus déclaré « sufficient » avec moins de {min_useful} documents")
    if output.status == ReviewStatus.ready_for_verification and not output.limits_of_this_review:
        violations.append("R9: aucune limite de la revue déclarée")

    # R10 — l'agent ne s'auto-valide jamais
    if output.validation.verified is True:
        violations.append("R10: l'agent a posé validation.verified=true (réservé au vérificateur)")
    if output.validation.verifier_status != "pending":
        violations.append("R10: verifier_status doit rester 'pending' à la sortie de l'agent")

    return violations


def _anchored(quote: str, source_text: str, abstract: str) -> bool:
    """La citation doit exister dans le texte lu, ou à défaut dans le résumé fourni."""
    from ..sources.fulltext import is_quote_anchored

    if source_text and is_quote_anchored(quote, source_text):
        return True
    if abstract and is_quote_anchored(quote, abstract):
        return True
    return False


def validate_final(output: ReviewOutput) -> list[str]:
    """Contrôles finaux de forme et de cohérence globale."""
    violations: list[str] = []
    if output.status == ReviewStatus.needs_clarification and not output.clarification_questions:
        violations.append("R11: needs_clarification sans question posée à l'étudiant")
    if output.status == ReviewStatus.blocked and not (output.unknowns or output.limits_of_this_review):
        violations.append("R11: blocked sans explication")
    if output.status == ReviewStatus.ready_for_verification and not output.corpus.documents:
        violations.append("R11: ready_for_verification sans aucun document dans le corpus")
    return violations
