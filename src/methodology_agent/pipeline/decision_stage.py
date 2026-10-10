"""Portillon humain : décision de l'étudiant / de l'encadreur (SPEC §12).

L'agent ne peut JAMAIS s'attribuer `validated` : seule une décision explicite, après vérification,
produit ce statut. L'étudiant peut accepter, modifier le protocole ou refuser.
"""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.output import DocumentStatus, MethodologyStatus
from . import protocol_checks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply(output, decision, request) -> tuple:
    """Applique la décision. Retourne (output, needs_revision, violations)."""
    if output.status not in (MethodologyStatus.awaiting_human_validation,
                             MethodologyStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"le protocole n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "le protocole doit d'abord être validé par le vérificateur avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = MethodologyStatus.validated
        output.document_status = DocumentStatus.valide
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = MethodologyStatus.blocked
        output.document_status = DocumentStatus.a_reviser
        return output, False, []

    # modified — l'étudiant corrige le protocole et/ou fournit des informations.
    modified = decision.modified or {}
    if not modified and not (decision.provided_information or "").strip():
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans changement fourni (champ `modified` ou "
            "`provided_information` requis)")

    protocol = output.protocol
    for key in ("approche", "logique", "type_recherche", "strategie", "terrain"):
        if isinstance(modified.get(key), str) and modified[key].strip():
            setattr(protocol, key, modified[key].strip())
    echantillonnage = modified.get("echantillonnage")
    if isinstance(echantillonnage, dict):
        for key in ("taille_texte", "justification", "sans_objet_raison"):
            if isinstance(echantillonnage.get(key), str) and echantillonnage[key].strip():
                setattr(protocol.echantillonnage, key, echantillonnage[key].strip())
        if isinstance(echantillonnage.get("taille"), int):
            protocol.echantillonnage.taille = echantillonnage["taille"]
            if (echantillonnage.get("justification") or "").strip():
                from ..schemas.protocol import SourceTaille
                protocol.echantillonnage.source_taille = SourceTaille.fournie
    terrain_autorise = modified.get("autorisations_obtenues")
    if isinstance(terrain_autorise, str) and terrain_autorise.strip():
        protocol.ethique.autorisations_obtenues = terrain_autorise.strip()
    if (decision.provided_information or "").strip():
        output.informations_a_confirmer.append(
            "informations complémentaires fournies par l'étudiant : "
            + decision.provided_information.strip())
        request.realise_preuves = list(request.realise_preuves or []) + [
            decision.provided_information.strip()]

    violations = protocol_checks.run(request, output.protocol, output.matrice, output.draft,
                                     output.analysis)
    if violations:
        return output, True, violations
    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = MethodologyStatus.ready_for_verification
    output.document_status = DocumentStatus.a_verifier
    return output, True, []


def apply_corrections(output, values: list[str]) -> None:
    """Enregistre des corrections demandées sans rejouer la campagne (usage interne)."""
    output.historique_modifications.extend(str(v) for v in values if str(v).strip())
