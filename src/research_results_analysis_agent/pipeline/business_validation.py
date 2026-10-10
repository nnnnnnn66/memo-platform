"""Validation métier de l'étape 10 (S1–S6) : socle, statut, anti-invention, honnêteté.

Le fond reste au vérificateur : ici, seuls des invariants objectifs.
"""

from ..schemas.output import DocumentStatus, ResultsOutput, ResultsStatus


def validate_semantics(output: ResultsOutput, request) -> list[str]:
    violations: list[str] = []

    # S1 — le socle : sujet, question et méthodologie validée.
    if not request.effective_subject().strip():
        violations.append("S1: aucun sujet de référence")
    if not request.effective_question().strip():
        violations.append("S1: aucune question de recherche de référence")
    if request.upstream_methodology is None:
        violations.append("S1: aucune méthodologie validée de l'étape 9 rattachée")

    # S2 — statut : seul l'état FINAL exige la vérification réussie.
    if output.status in (ResultsStatus.awaiting_human_validation, ResultsStatus.validated):
        if not output.plan.analyses_realisees and not output.plan.plan_seulement:
            violations.append("S2: aucune analyse réalisée ni déclarée, pour une production "
                              "présentée à la validation")
    if output.document_status == DocumentStatus.valide and not output.verification_result.verified:
        violations.append("S2: document marqué « validé » sans vérification indépendante réussie")
    if output.document_status == DocumentStatus.valide and output.status != ResultsStatus.validated:
        violations.append("S2: document marqué « validé » alors que le pipeline n'a pas atteint "
                          "l'état validé (décision humaine manquante)")

    # S3 — tout résultat affirmé référence un calcul réel.
    ids = output.computed_results.ids()
    for resultat in output.plan.resultats or []:
        reference = str(resultat.id_resultat or "").strip()
        if not reference or reference not in ids:
            violations.append(
                "S3: un résultat affirmé ne renvoie pas à un calcul réalisé "
                f"(référence « {reference or 'vide'} »)")
            break

    # S4 — les chiffres du document doivent venir du moteur (liste blanche numérique).
    from ..analysis import results_rules
    from . import results_checks
    numeric = results_rules.run_checks(request, output.computed_results, output.plan,
                                       output.interpretation, output.draft, output.inventory)
    for violation in numeric:
        if violation.startswith("Q2") and violation not in violations:
            violations.append("S4: " + violation)
            break
    assert results_checks is not None

    # S5 — les données personnelles RÉELLEMENT repérées doivent conduire à déclarer l'anonymisation.
    personnelles = [d for d in output.inventory.donnees_personnelles
                    if str(d).strip() and not str(d).lower().startswith(("aucun", "pas de", "néant"))]
    if personnelles and not any(
            "anonym" in str(c).lower() for c in output.inventory.anomalies
            + output.limits_of_this_output + output.informations_a_confirmer
            + output.inventory.manquants):
        violations.append("S5: des données personnelles ont été repérées mais l'anonymisation n'est "
                          "pas mentionnée")

    # S6 — aucune auto-vérification ni auto-validation.
    if output.status == ResultsStatus.ready_for_verification and output.verification_result.verified:
        violations.append("S6: verification_result.verified posé par l'agent (réservé au vérificateur)")
    if output.status == ResultsStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted:
            violations.append("S6: statut 'validated' sans acceptation étudiante "
                              "(réservé au portillon humain)")
    return violations


def validate_final(output: ResultsOutput) -> list[str]:
    violations: list[str] = []
    if output.status == ResultsStatus.needs_clarification and not output.questions_for_human:
        violations.append("S5: needs_clarification sans question posée à l'étudiant")
    if output.status == ResultsStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted or not output.verification_result.verified:
            violations.append("S5: 'validated' sans acceptation étudiante ET vérification réussie")
    if output.status == ResultsStatus.blocked and not (
            output.student_validation.decision
            and output.student_validation.decision.value == "refused"):
        if not (output.unknowns or output.limits_of_this_output):
            violations.append("S5: 'blocked' sans explication")
    return violations
