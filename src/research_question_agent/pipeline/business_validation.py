"""Validation métier : anti-fusion, neutralité, honnêteté, statuts (SPEC §10, §13).

Contrôles déterministes sur la production assemblée, AVANT le vérificateur.
"""

import unicodedata

from ..analysis import intent as intent_module
from ..schemas.output import QuestionOutput, QuestionStatus

# Marqueurs des étapes suivantes (produites ailleurs) ou d'une validation non acquise.
FORBIDDEN_MARKERS = [
    "hypothèses de recherche",
    "plan de mémoire",
    "méthodologie détaillée",
    "question validée par le directeur",
    "objectifs spécifiques définitifs",
]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.split())


def validate_semantics(output: QuestionOutput, request, problematic_text: str) -> list[str]:
    violations: list[str] = []

    # R1 — franchise du socle : la question découle d'une problématique fournie
    if not (problematic_text or "").strip():
        violations.append("R1: aucune problématique de référence (le socle de la question)")

    # R2 — anti-fusion : la question n'est ni la problématique, ni le sujet
    question = _normalize(output.main_research_question)
    if question:
        if question == _normalize(problematic_text):
            violations.append("R2: la « question » recopie la problématique (fusion interdite)")
        if question == _normalize(request.effective_subject()):
            violations.append("R2: la « question » recopie le sujet (fusion interdite)")
    blob = " ".join([output.main_research_question, output.formulation_rationale,
                     " ".join(output.secondary_research_questions)]).lower()
    for marker in FORBIDDEN_MARKERS:
        if marker in blob:
            violations.append(f"R2: empiètement sur une étape suivante détecté (« {marker} »)")

    # R3 — intention dans l'enum canonique
    if not intent_module.is_known(output.research_intention.intention):
        violations.append("R3: intention de recherche hors enum canonique")

    # R4 — complétude selon le statut
    if output.status in (QuestionStatus.ready_for_verification,
                         QuestionStatus.awaiting_human_validation, QuestionStatus.validated):
        if not output.main_research_question.strip():
            violations.append("R4: statut de proposition sans question principale")
        if not any(d.strip() for d in (output.formulation_rationale or "").split()):
            violations.append("R4: aucune justification de formulation")
    if output.status == QuestionStatus.awaiting_human_validation and not output.verification_result.verified:
        violations.append("R4: awaiting_human_validation sans vérification réussie")

    # R5 — l'agent ne s'auto-vérifie jamais
    if output.status == QuestionStatus.ready_for_verification and output.verification_result.verified:
        violations.append("R5: verification_result.verified posé par l'agent (réservé au vérificateur)")
    # `validated` n'est légitime QUE par une décision étudiante explicite (portillon humain).
    if output.status == QuestionStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted:
            violations.append(
                "R5: statut 'validated' sans acceptation étudiante (réservé au portillon humain)")

    # R6 — délimitation ajoutée sans source ⇒ doit être déclarée dans les limites
    if output.scope_and_boundaries.added_without_source:
        declared = any("délimitation" in note.lower() for note in output.limits_of_this_output)
        if not declared:
            violations.append("R6: délimitation ajoutée sans source mais non déclarée dans les limites")

    return violations


def validate_final(output: QuestionOutput) -> list[str]:
    violations: list[str] = []
    if output.status == QuestionStatus.needs_clarification and not output.clarification_questions:
        violations.append("R7: needs_clarification sans question posée à l'étudiant")
    if output.status == QuestionStatus.validated:
        accepted = output.student_validation.decision is not None and \
            output.student_validation.decision.value == "accepted"
        if not accepted or not output.verification_result.verified:
            violations.append("R7: 'validated' sans acceptation étudiante ET vérification réussie")
    if output.status == QuestionStatus.blocked and not (
            output.student_validation.decision and output.student_validation.decision.value == "refused"):
        # blocked peut aussi venir d'un manque de matière : une trace d'explication est requise.
        if not (output.unknowns or output.limits_of_this_output):
            violations.append("R7: 'blocked' sans explication (unknowns/limites)")
    return violations
