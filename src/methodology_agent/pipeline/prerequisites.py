"""Pré-cadrage (SPEC §5, §14) : un protocole peut-il être établi ?

Déterministe. Le point de départ de l'étape 9 est le DIAGNOSTIC VALIDÉ de l'étape 8 : sans lui, aucun
protocole défendable ne peut être produit (le diagnostic serait alors re-tranché par la porte de
derrière). Un prérequis essentiel manquant arrête la production AVANT tout appel LLM.
"""


def check(request) -> dict:
    """Retourne {needs_clarification, questions, defaults_used, blockers}."""
    blockers: list[str] = []
    questions: list[str] = []

    diagnostic = request.upstream_methodology_diagnostic
    if diagnostic is None:
        blockers.append("le diagnostic méthodologique vérifié de l'étape 8")
        questions.append(
            "Pouvez-vous transmettre le diagnostic méthodologique vérifié (étape 8, avec le verdict "
            "du vérificateur et votre décision) ? La méthodologie de l'étape 9 le développe — elle "
            "ne le remplace pas.")
    else:
        if not diagnostic.is_verified:
            blockers.append("un diagnostic de l'étape 8 dont le vérificateur a validé le contenu")
            questions.append(
                "Le diagnostic transmis n'est pas marqué vérifié. Finalisez l'étape 8 (vérificateur "
                "puis décision) ou confirmez explicitement votre validation.")
        status = request.diagnostic_status()
        if status not in ("valide", "en_attente_de_validation"):
            blockers.append("un diagnostic dont le statut est « validé » ou « en attente de validation »")
            questions.append(
                f"Le statut du diagnostic est « {status or 'inconnu'} ». Un diagnostic provisoire ou "
                "à réviser ne peut pas fonder un protocole définitif.")

    if not request.effective_subject().strip():
        blockers.append("le sujet exact du mémoire")
        questions.append("Pouvez-vous préciser le sujet exact du mémoire ?")

    if not request.effective_question().strip():
        blockers.append("la question de recherche principale")
        questions.append(
            "Pouvez-vous transmettre la question de recherche principale validée ? Sans elle, aucun "
            "protocole ne peut être argumenté.")

    defaults_used: list[str] = []
    if not (request.target_population or "").strip():
        defaults_used.append(
            "population non précisée : la population cible et l'échantillonnage restent à confirmer")
    if not (request.field_access or "").strip():
        defaults_used.append("accès au terrain non précisé : faisabilité à confirmer")
    if not (request.available_data or "").strip():
        defaults_used.append("données disponibles non précisées : origine des données à confirmer")
    if not (request.available_resources or "").strip():
        defaults_used.append("ressources (temps, budget, moyens) non précisées : faisabilité à confirmer")
    if not (request.university_instructions or "").strip():
        defaults_used.append(
            "consignes de l'établissement non fournies : la structure proposée suit les usages "
            "courants et n'est présentée comme une règle d'établissement dans aucun cas")
    if request.hypotheses_not_required():
        defaults_used.append(
            "l'étape 7 a conclu qu'aucune hypothèse n'est pertinente : aucune hypothèse ne sera "
            "ajoutée")

    return {
        "needs_clarification": bool(blockers),
        "questions": questions,
        "defaults_used": defaults_used,
        "blockers": blockers,
    }
