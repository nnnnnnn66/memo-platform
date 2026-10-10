"""Validation métier de l'audit (T1–T6) : socle, statuts, fondement, confidentialité, intégrité."""

import re

from ..schemas.audit import Severite
from ..schemas.report import verdict_from
from ..schemas.output import AuditStatus, CoherenceOutput, DocumentStatus

#: Données personnelles qui ne doivent JAMAIS apparaître dans un rapport d'audit.
_PERSONNEL = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    re.compile(r"(?<!\d)(?:\+?\d[\s.-]?){9,}(?!\d)"),
    re.compile(r"(?i)\b(?:nom|pr[ée]nom)\s*:\s*\S+"),
]


def _rapport_textuel(output: CoherenceOutput) -> str:
    morceaux = [output.report.synthese]
    morceaux += [c.constat for c in output.audit.constats]
    morceaux += [c.preuve for c in output.audit.constats]
    morceaux += [c.recommandation for c in output.audit.constats]
    morceaux += [item.element + " " + item.raison for item in output.non_verifiable]
    return " \n ".join(str(m or "") for m in morceaux)


def validate_semantics(output: CoherenceOutput, request) -> list[str]:
    violations: list[str] = []
    constats = output.audit.constats

    # T1 — le socle de l'audit.
    if len(output.etapes_presentes) < 2:
        violations.append("T1: moins de deux étapes exploitables : aucun audit transversal possible")
    if not request.effective_subject().strip():
        violations.append("T1: sujet absent du dossier")
    if not request.effective_question().strip():
        violations.append("T1: question de recherche absente du dossier")

    # T2 — cohérence des statuts.
    if output.status in (AuditStatus.awaiting_human_validation, AuditStatus.validated):
        if not constats and output.report.verdict.value != "coherent":
            violations.append("T2: verdict non « cohérent » sans aucun constat")
        if not output.report.synthese.strip():
            violations.append("T2: rapport sans synthèse")
    if output.document_status == DocumentStatus.valide and not output.verification_result.verified:
        violations.append("T2: rapport marqué « validé » sans contrôle réussi")
    if output.document_status == DocumentStatus.valide and output.status != AuditStatus.validated:
        violations.append("T2: rapport marqué « validé » alors que la décision humaine manque")

    # T3 — fondement et hiérarchie : tout constat porte preuve ET recommandation.
    for constat in constats:
        if not str(constat.preuve or "").strip():
            violations.append(f"T3: constat sans preuve « {constat.constat[:60]} »")
            break
        if not str(constat.recommandation or "").strip():
            violations.append(f"T3: constat sans recommandation « {constat.constat[:60]} »")
            break
    attendu = verdict_from(constats)
    if output.report.verdict.value != attendu.value:
        violations.append(f"T3: verdict « {output.report.verdict.value} » hors grille attendue "
                          f"« {attendu.value} »")

    # T4 — confidentialité : aucune donnée personnelle dans le rapport.
    blob = _rapport_textuel(output)
    if any(motif.search(blob) for motif in _PERSONNEL):
        violations.append("T4: le rapport reproduit des données personnelles (courriel, numéro, nom)")

    # T5 — le statut « contrôlé » ne peut venir que du contrôleur.
    if output.document_status == DocumentStatus.controle and not output.verification_result.verified:
        violations.append("T5: rapport marqué « contrôlé » sans verdict du contrôleur de l'audit")

    # T6 — aucune auto-validation.
    if output.status == AuditStatus.ready_for_verification and output.verification_result.verified:
        violations.append("T6: verification_result.verified posé par l'agent (réservé au contrôleur)")
    if output.status == AuditStatus.validated:
        decide = output.student_validation.decision
        if decide is None or getattr(decide, "value", decide) != "accepted":
            violations.append("T6: statut 'validated' sans acceptation de l'étudiant")
    return violations


def validate_final(output: CoherenceOutput) -> list[str]:
    violations: list[str] = []
    if output.status == AuditStatus.needs_clarification and not output.questions_for_human:
        violations.append("T5: needs_clarification sans question posée à l'étudiant")
    if output.status == AuditStatus.validated:
        decide = output.student_validation.decision
        accepte = decide is not None and getattr(decide, "value", decide) == "accepted"
        if not accepte or not output.verification_result.verified:
            violations.append("T5: 'validated' sans acceptation étudiante ET contrôle réussi")
    if output.status == AuditStatus.blocked and not output.unknowns \
            and not output.limites_de_cet_audit:
        violations.append("T5: 'blocked' sans explication")
    # Aucun constat bloquant sans mention dans la synthèse du rapport.
    if any(c.severite == Severite.bloqueur for c in output.audit.constats) \
            and not output.report.synthese.strip():
        violations.append("T5: constats bloquants sans synthèse")
    return violations
