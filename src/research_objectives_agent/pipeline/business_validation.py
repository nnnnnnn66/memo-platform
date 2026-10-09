"""Validation métier : anti-fusion, neutralité, honnêteté, statuts (SPEC §10, §13).

Contrôles déterministes sur la production assemblée, AVANT le vérificateur.
"""

import unicodedata

from ..analysis import objective_rules
from ..schemas.output import ObjectiveStatus, ObjectivesOutput

# Marqueurs des étapes suivantes (produites ailleurs) — un objectif n'est ni une hypothèse ni un plan.
FORBIDDEN_MARKERS = [
    "hypothèses de recherche",
    "h1 :", "h2 :", "h3 :",
    "plan de mémoire",
    "méthodologie détaillée",
    "objectifs validés par le directeur",
]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.split())


def validate_semantics(output: ObjectivesOutput, request, question_text: str) -> list[str]:
    violations: list[str] = []

    # R1 — franchise du socle : les objectifs découlent d'une question fournie
    if not (question_text or "").strip():
        violations.append("R1: aucune question de recherche de référence (le socle des objectifs)")

    # R2 — anti-fusion : l'objectif général n'est ni la question, ni le sujet, ni une hypothèse
    general = _normalize(output.general_objective)
    if general:
        if question_text and general == _normalize(question_text).rstrip("?"):
            violations.append("R2: l'objectif général recopie la question (fusion interdite)")
        if general == _normalize(request.effective_subject()):
            violations.append("R2: l'objectif général recopie le sujet (fusion interdite)")
    blob = " ".join([output.general_objective, output.objective_rationale,
                     " ".join(output.specific_objectives)]).lower()
    for marker in FORBIDDEN_MARKERS:
        if marker in blob:
            violations.append(f"R2: empiètement sur une étape suivante détecté (« {marker} »)")

    # R3 — complétude selon le statut
    if output.status in (ObjectiveStatus.ready_for_verification,
                         ObjectiveStatus.awaiting_human_validation, ObjectiveStatus.validated):
        if not output.general_objective.strip():
            violations.append("R3: statut de proposition sans objectif général")
        if not [o for o in output.specific_objectives if str(o).strip()]:
            violations.append("R3: statut de proposition sans objectif spécifique")
        if not (output.objective_rationale or "").strip():
            violations.append("R3: aucune justification des objectifs")
    if output.status == ObjectiveStatus.awaiting_human_validation \
            and not output.verification_result.verified:
        violations.append("R3: awaiting_human_validation sans vérification réussie")

    # R4 — l'agent ne s'auto-vérifie jamais
    if output.status == ObjectiveStatus.ready_for_verification and output.verification_result.verified:
        violations.append("R4: verification_result.verified posé par l'agent (réservé au vérificateur)")
    if output.status == ObjectiveStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted:
            violations.append(
                "R4: statut 'validated' sans acceptation étudiante (réservé au portillon humain)")

    # R5 — délimitation ajoutée sans source ⇒ doit être déclarée dans les limites
    if output.scope_and_boundaries.added_without_source:
        declared = any("délimitation" in note.lower() for note in output.limits_of_this_output)
        if not declared:
            violations.append("R5: délimitation ajoutée sans source mais non déclarée dans les limites")

    return violations


def validate_final(output: ObjectivesOutput) -> list[str]:
    violations: list[str] = []
    if output.status == ObjectiveStatus.needs_clarification and not output.clarification_questions:
        violations.append("R6: needs_clarification sans question posée à l'étudiant")
    if output.status == ObjectiveStatus.validated:
        accepted = output.student_validation.decision is not None and \
            output.student_validation.decision.value == "accepted"
        if not accepted or not output.verification_result.verified:
            violations.append("R6: 'validated' sans acceptation étudiante ET vérification réussie")
    if output.status == ObjectiveStatus.blocked and not (
            output.student_validation.decision
            and output.student_validation.decision.value == "refused"):
        if not (output.unknowns or output.limits_of_this_output):
            violations.append("R6: 'blocked' sans explication (unknowns/limites)")
    return violations


def forbidden_hypothesis_markers(output: ObjectivesOutput) -> list[str]:
    """Expose les tournures d'hypothèse détectées dans les objectifs (complément des checks O2)."""
    texts = [output.general_objective] + list(output.specific_objectives)
    hits: list[str] = []
    for text in texts:
        hits.extend(objective_rules.looks_like_hypothesis(text))
    return hits
