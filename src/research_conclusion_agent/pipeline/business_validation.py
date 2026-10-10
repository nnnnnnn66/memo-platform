"""Validation métier de l'étape 11 (T1–T6) : socle, statut, traçabilité, confidentialité."""

import re

from ..schemas.output import ConclusionOutput, ConclusionStatus, DocumentStatus

#: Motifs de données personnelles qui ne doivent JAMAIS être recopiées dans la conclusion (SPEC §10.11).
_PERSONNEL = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    re.compile(r"(?<!\d)(?:\+?\d[\s.-]?){9,}(?!\d)"),
    re.compile(r"(?i)\b(?:nom|pr[ée]nom)\s*:\s*\S+"),
]


def _contient_donnees_personnelles(output) -> bool:
    blob = " ".join(list(output.draft.limites or []) + list(output.draft.perspectives or [])
                    + [s.contenu for s in output.draft.sections or []]
                    + [s.justification for s in output.draft.sections or []]
                    + [output.synthesis.reponse_question.reponse])
    return any(pattern.search(blob or "") for pattern in _PERSONNEL)


def validate_semantics(output: ConclusionOutput, request) -> list[str]:
    violations: list[str] = []

    # T1 — le socle : question de recherche et résultats vérifiés de l'étape 10.
    if not request.effective_question().strip():
        violations.append("T1: aucune question de recherche de référence")
    if request.upstream_results is None:
        violations.append("T1: aucun résultat de l'étape 10 rattaché")

    # T2 — cohérence des statuts.
    if output.status in (ConclusionStatus.awaiting_human_validation, ConclusionStatus.validated):
        if not str(output.synthesis.reponse_question.reponse or "").strip() \
                and not output.synthesis.plan_seulement:
            violations.append("T2: conclusion sans réponse à la question de recherche")
        if not output.draft.sections and not output.synthesis.plan_seulement:
            violations.append("T2: conclusion sans aucune section rédigée")
    if output.document_status == DocumentStatus.valide and not output.verification_result.verified:
        violations.append("T2: document marqué « validé » sans vérification indépendante réussie")
    if output.document_status == DocumentStatus.valide \
            and output.status != ConclusionStatus.validated:
        violations.append("T2: document marqué « validé » alors que le pipeline n'a pas atteint "
                          "l'état validé (décision humaine manquante)")

    # T3 — traçabilité : un bilan d'objectif doit être déclaré, et tout manque doit être annoncé.
    if not output.synthesis.plan_seulement and not output.synthesis.bilan_objectifs \
            and not output.synthesis.elements_manquants:
        violations.append("T3: aucun bilan des objectifs et aucun manque déclaré : la conclusion ne "
                          "dit pas ce que le travail a permis d'établir")

    # T4 — aucune donnée personnelle recopiée (SPEC §10.11).
    if _contient_donnees_personnelles(output):
        violations.append("T4: la conclusion reproduit des données personnelles (courriel, numéro, "
                          "nom). Ces éléments ne doivent pas y figurer.")

    # T5 — un document « vérifié » ne peut l'être que par le vérificateur.
    if output.document_status == DocumentStatus.verifie and not output.verification_result.verified:
        violations.append("T5: document marqué « vérifié » sans verdict du vérificateur")

    # T6 — aucune auto-vérification ni auto-validation.
    if output.status == ConclusionStatus.ready_for_verification and output.verification_result.verified:
        violations.append("T6: verification_result.verified posé par l'agent (réservé au vérificateur)")
    if output.status == ConclusionStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted:
            violations.append("T6: statut 'validated' sans acceptation étudiante "
                              "(réservé au portillon humain)")
    return violations


def validate_final(output: ConclusionOutput) -> list[str]:
    violations: list[str] = []
    if output.status == ConclusionStatus.needs_clarification and not output.questions_for_human:
        violations.append("T5: needs_clarification sans question posée à l'étudiant")
    if output.status == ConclusionStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted or not output.verification_result.verified:
            violations.append("T5: 'validated' sans acceptation étudiante ET vérification réussie")
    if output.status == ConclusionStatus.blocked and not (
            output.student_validation.decision
            and output.student_validation.decision.value == "refused"):
        if not (output.unknowns or output.limits_of_this_output):
            violations.append("T5: 'blocked' sans explication")
    return violations
