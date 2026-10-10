"""Validation métier de l'étape 9 (R1–R6) : le socle, le statut du document, l'honnêteté.

Même famille de règles que les autres agents : elles ne jugent pas le fond (vérificateur) mais
empêchent qu'une sortie manifestement incohérente soit transmise ou marquée validée.
"""

from ..analysis import matrix_rules
from ..schemas.output import DocumentStatus, MethodologyOutput, MethodologyStatus


def validate_semantics(output: MethodologyOutput, request) -> list[str]:
    violations: list[str] = []

    # R1 — le socle : sans sujet, question et objectifs, aucun protocole n'est défendable.
    if not request.effective_subject().strip():
        violations.append("R1: aucun sujet de référence")
    if not request.effective_question().strip():
        violations.append("R1: aucune question de recherche de référence")
    if not request.diagnostic_status():
        violations.append("R1: aucun diagnostic de l'étape 8 rattaché")

    # R2 — cohérence du statut de document.
    if output.status in (MethodologyStatus.awaiting_human_validation, MethodologyStatus.validated):
        if not str(output.protocol.approche or "").strip():
            violations.append("R2: protocole sans approche reprise de l'étape 8")
        if not output.protocol.analyses:
            violations.append("R2: protocole sans méthode d'analyse")
        if not output.matrice.lignes:
            violations.append("R2: matrice de cohérence vide")
    if output.status == MethodologyStatus.awaiting_human_validation \
            and not output.verification_result.verified:
        violations.append("R2: awaiting_human_validation sans vérification réussie")
    # Un document se présente à la validation AVEC ses réserves déclarées : c'est le rôle du
    # portillon humain de les arbitrer. Seul le statut FINAL « valide » exige que la vérification
    # ait réussi (une règle trop stricte ici refusait une sortie pourtant vérifiée — leçon R2/R7).
    if output.document_status == DocumentStatus.valide and not output.verification_result.verified:
        violations.append("R2: document marqué « validé » sans vérification indépendante réussie")

    # R3 — cohérence statut de document / statut de pipeline : un document ne peut être marqué
    # « validé » que si le pipeline a atteint l'état `validated` (posé par la décision humaine).
    if output.document_status == DocumentStatus.valide \
            and output.status != MethodologyStatus.validated:
        violations.append(
            "R3: document marqué « validé » alors que le pipeline n'a pas atteint l'état validé "
            "(décision humaine manquante)")
    # Et toute contradiction relevée par l'analyse doit être DÉCLARÉE dans la sortie.
    if output.analysis.contradictions and not output.contradictions:
        violations.append("R3: contradictions relevées à l'analyse mais non déclarées en sortie")

    # R4 — aucun objectif orphelin : chaque objectif vérifié a une ligne de matrice.
    orphans = matrix_rules.orphan_objectives(request, output.matrice)
    if orphans:
        violations.append("R4: objectif(s) sans ligne de matrice : " + " ; ".join(orphans))

    # R5 — si la recherche touche des personnes, l'éthique doit être traitée.
    terrain = any(
        word in " ".join(str(t.nom or "").lower() for t in output.protocol.techniques)
        for word in ("questionnaire", "entretien", "observation", "sondage"))
    if terrain and not output.protocol.ethique.concerne_personnes:
        violations.append(
            "R5: une collecte impliquant des personnes est prévue mais l'éthique n'est pas traitée "
            "(consentement, anonymisation, autorisations)")
    if output.protocol.ethique.autorisations_obtenues \
            and not output.protocol.ethique.autorisations_preuve:
        violations.append(
            "R5: une autorisation est déclarée OBTENUE sans preuve fournie")

    # R6 — l'agent ne s'auto-vérifie ni ne s'auto-valide.
    if output.status == MethodologyStatus.ready_for_verification \
            and output.verification_result.verified:
        violations.append("R6: verification_result.verified posé par l'agent (réservé au vérificateur)")
    if output.status == MethodologyStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted:
            violations.append(
                "R6: statut 'validated' sans acceptation étudiante (réservé au portillon humain)")
    return violations


def validate_final(output: MethodologyOutput) -> list[str]:
    violations: list[str] = []
    if output.status == MethodologyStatus.needs_clarification and not output.questions_for_human:
        violations.append("R5: needs_clarification sans question posée à l'étudiant")
    if output.status == MethodologyStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted or not output.verification_result.verified:
            violations.append(
                "R5: 'validated' sans acceptation étudiante ET vérification réussie")
    if output.status == MethodologyStatus.blocked and not (
            output.student_validation.decision
            and output.student_validation.decision.value == "refused"):
        if not (output.unknowns or output.limits_of_this_output):
            violations.append("R5: 'blocked' sans explication (unknowns/limites)")
    return violations
