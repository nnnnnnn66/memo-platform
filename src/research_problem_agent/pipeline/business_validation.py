"""Validation métier de la sortie de l'Agent Problème.

Retourne la liste des violations (liste vide = conforme). Contrôles déterministes :
fidélité, anti-fusion, distinction fait/interprétation/inconnu, cohérence du statut, et
surtout ANCRAGE STRICT des sources : une référence inventée ne peut pas passer (SPEC §10.1-6,
§13, §16.B-C).
"""

from ..schemas.input import ProblemRequest
from ..schemas.output import (
    Nature,
    ProblemOutput,
    ProblemStatus,
    Provenance,
    VerificationStatus,
)
from ..schemas.search_intent import Phase1Output

# Formulations qui trahiraient une étape suivante produite à la place de l'étudiant.
_FORBIDDEN_MARKERS = [
    "problématique",
    "question de recherche",
    "question principale",
    "hypothèse",
    "hypothèses",
    "plan de mémoire",
    "objectifs de recherche",
]


def validate_phase1(phase1: Phase1Output, limits) -> list[str]:
    violations: list[str] = []
    if phase1.needs_search and not phase1.search_intents:
        violations.append("P1: needs_search=true mais aucune requête de recherche fournie")
    if not phase1.preliminary_analysis.phenomenon and not phase1.preliminary_analysis.main_concepts:
        violations.append("P1: analyse préliminaire vide (ni phénomène ni concepts)")
    if len(phase1.search_intents) > limits.max_search_queries:
        violations.append(
            f"P1: trop de requêtes proposées ({len(phase1.search_intents)} > "
            f"{limits.max_search_queries})"
        )
    return violations


def _free_texts(output: ProblemOutput) -> str:
    return " ".join([
        output.identified_problem.statement,
        output.identified_problem.situation,
        output.identified_problem.why_problematic,
        output.provisional_formulation,
        output.subject_reference.reformulated,
        " ".join(output.identified_problem.consequences),
        " ".join(output.identified_problem.stakes),
    ])


def validate_business(request: ProblemRequest, output: ProblemOutput, source_set) -> list[str]:
    violations: list[str] = []

    # R1 — fidélité : subject_reference.original identique au sujet reçu
    if output.subject_reference.original.strip() != request.subject_text.strip():
        violations.append("R1: subject_reference.original ne correspond pas exactement au sujet reçu")

    # R2 — anti-fusion : aucune étape suivante produite à la place de l'étudiant
    blob = _free_texts(output).lower()
    for marker in _FORBIDDEN_MARKERS:
        if marker in blob:
            violations.append(f"R2: fusion interdite détectée (marqueur « {marker} »)")

    # R3 — ancrage strict des sources citées
    for i, source in enumerate(output.sources):
        record = source_set.by_id(source.source_id) if source_set else None
        if record is None:
            violations.append(
                f"R3: sources[{i}] référence un source_id inexistant ({source.source_id!r}) — "
                "référence inventée interdite"
            )
            continue
        if not source.url.strip():
            violations.append(f"R3: sources[{i}] (source_id={record.source_id}) est citée sans URL")
        if source.url.strip().lower().rstrip("/") != record.url.strip().lower().rstrip("/"):
            violations.append(
                f"R3: sources[{i}] (source_id={record.source_id}) a une URL qui ne correspond "
                "pas à celle réellement récupérée"
            )
        if source.source_type.value != record.source_type:
            violations.append(
                f"R3: sources[{i}] déclare source_type={source.source_type.value} alors que le "
                f"fournisseur est de type {record.source_type}"
            )
        if (source.verification_status == VerificationStatus.verified
                and not record.retrieved):
            violations.append(f"R3: sources[{i}] marquée verified alors qu'elle n'est pas récupérée")
        if record.doi and source.doi and source.doi.strip().lower() != record.doi.strip().lower():
            violations.append(f"R3: sources[{i}] DOI incohérent avec la source récupérée")

    # R4 — éléments justificatifs : traçabilité et distinction fait/interprétation/inconnu
    for i, element in enumerate(output.justifying_elements):
        if element.source_id:
            if source_set is None or source_set.by_id(element.source_id) is None:
                violations.append(
                    f"R4: justifying_elements[{i}] cite un source_id inexistant "
                    f"({element.source_id!r})"
                )
            if element.provenance != Provenance.external:
                violations.append(
                    f"R4: justifying_elements[{i}] cite une source ({element.source_id}) mais "
                    f"déclare provenance={element.provenance} au lieu de « external »"
                )
        elif element.provenance == Provenance.external:
            violations.append(
                f"R4: justifying_elements[{i}] déclare provenance=external sans source_id"
            )
        if element.nature == Nature.fact and element.provenance == Provenance.inferred:
            violations.append(
                f"R4: justifying_elements[{i}] présente une déduction comme un fait"
            )
        if (element.nature == Nature.fact and not element.source_id
                and element.provenance not in (Provenance.provided, Provenance.unknown)):
            violations.append(
                f"R4: justifying_elements[{i}] énonce un fait sans source et non fourni par "
                "l'étudiant (invention probable)"
            )

    # R5 — cohérence du statut et de la délimitation
    if output.status == ProblemStatus.ready_for_verification:
        if not output.identified_problem.statement.strip():
            violations.append("R5: ready_for_verification sans problème identifié")
        if not output.provisional_formulation.strip():
            violations.append("R5: ready_for_verification sans formulation provisoire")
    if output.status == ProblemStatus.needs_clarification and not output.remaining_questions:
        violations.append("R5: needs_clarification sans question posée à l'étudiant")
    if output.status == ProblemStatus.blocked and not output.gaps and not output.unknown_information:
        violations.append("R5: blocked sans explication (gaps/unknown_information vides)")

    # R6 — aucun fait externe sans source quand des sources existent et aucune n'est citée
    external_facts = [
        e for e in output.justifying_elements
        if e.nature == Nature.fact and e.provenance == Provenance.external
    ]
    if external_facts and not output.sources:
        violations.append(
            "R6: des faits externes sont affirmés alors qu'aucune source n'est citée"
        )

    # R7 — l'agent ne s'auto-valide jamais
    if output.validation.verified is True:
        violations.append("R7: l'agent a posé validation.verified=true (réservé au vérificateur)")
    if output.validation.verifier_status != "pending":
        violations.append("R7: verifier_status doit rester 'pending' à la sortie de l'agent")

    return violations
