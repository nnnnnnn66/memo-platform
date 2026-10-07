"""Validation métier de la sortie (règles méthodologiques + anti-fusion).

Retourne la liste des violations. Liste vide = conforme.
"""

from ..schemas.input import SubjectRequest
from ..schemas.output import SubjectOutput, SubjectStatus, SourceType, VerificationStatus

# Formulations qui trahiraient une fusion interdite (problème/problématique/question/hypothèse).
_FORBIDDEN_MARKERS = [
    "problématique", "question de recherche", "hypothèse", "hypothèses",
    "objectif de recherche", "objectifs de recherche",
]


def validate_business(request: SubjectRequest, output: SubjectOutput) -> list[str]:
    violations: list[str] = []

    # R1 — fidélité : subject.original identique à l'entrée
    if output.subject.original.strip() != request.subject_text.strip():
        violations.append("R1: subject.original ne correspond pas exactement au sujet reçu")

    # R2 — anti-fusion : aucun marqueur d'étape suivante
    blob = " ".join([
        output.subject.reformulated,
        output.initial_justification,
        " ".join(output.key_concepts),
    ]).lower()
    for marker in _FORBIDDEN_MARKERS:
        if marker in blob:
            violations.append(f"R2: fusion interdite détectée (marqueur « {marker} »)")

    # R3 — cohérence du statut : si l'objet est vide, il faut clarifier
    if output.status == SubjectStatus.ready_for_verification:
        if not output.subject.reformulated and not output.research_context.object_of_study:
            violations.append("R3: statut ready_for_verification sans sujet ni objet exploitable")

    # R4 — traçabilité des preuves
    for i, ev in enumerate(output.evidence):
        if ev.source_type == SourceType.model_inference and ev.verification_status == VerificationStatus.verified:
            violations.append(f"R4: evidence[{i}] model_inference marquée verified (interdit)")
        if ev.source_type == SourceType.external and not (ev.source or ev.url):
            violations.append(f"R4: evidence[{i}] externe sans source ni url")

    # R5 — l'agent ne s'auto-valide pas
    if output.validation.verified is True:
        violations.append("R5: l'agent a posé validation.verified=true (réservé au vérificateur)")
    if output.validation.verifier_status != "pending":
        violations.append("R5: verifier_status doit rester 'pending' à la sortie de l'agent")

    # R6 — questions cohérentes avec le statut
    if output.status == SubjectStatus.needs_clarification and not output.questions_for_student:
        violations.append("R6: needs_clarification sans questions posées à l'étudiant")

    return violations
