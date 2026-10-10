"""Pré-cadrage (SPEC §5, §14) : une conclusion peut-elle être rédigée ?

Déterministe. Le point de départ est constitué des éléments VALIDÉS des étapes précédentes — en
particulier les résultats VÉRIFIÉS de l'étape 10. Sans eux, la conclusion se limite à un PLAN.
"""


def check(request) -> dict:
    blockers: list[str] = []
    questions: list[str] = []

    results = request.upstream_results
    if results is None:
        blockers.append("les résultats et analyses de l'étape 10")
        questions.append(
            "Pouvez-vous transmettre les résultats vérifiés (étape 10, avec le verdict du vérificateur "
            "et votre décision) ? Sans eux, aucune conclusion fondée ne peut être rédigée.")
    else:
        if not results.is_verified:
            blockers.append("des résultats dont le vérificateur a validé le contenu")
            questions.append(
                "Les résultats transmis ne sont pas marqués vérifiés. Finalisez l'étape 10 "
                "(vérificateur puis décision), ou confirmez explicitement votre validation.")
        status = request.results_status()
        if status not in ("valide", "en_attente_de_validation"):
            blockers.append("des résultats au statut « validé » ou « en attente de validation »")
            questions.append(
                f"Le statut des résultats est « {status or 'inconnu'} ». Des résultats provisoires ne "
                "peuvent pas fonder une conclusion.")

    if not request.effective_question().strip():
        blockers.append("la question de recherche principale")
        questions.append("Pouvez-vous transmettre la question de recherche principale validée ? La "
                         "conclusion doit y répondre explicitement.")
    if not request.effective_subject().strip():
        blockers.append("le sujet exact du mémoire")
        questions.append("Pouvez-vous préciser le sujet exact du mémoire ?")

    defaults_used: list[str] = []
    if not request.available_results():
        defaults_used.append(
            "aucun résultat vérifié exploitable : la production se limitera à un PLAN de conclusion "
            "et aux informations à recueillir — aucune conclusion ne sera rédigée")
    if request.hypotheses_not_required():
        defaults_used.append(
            "l'étape 7 a conclu qu'aucune hypothèse n'est pertinente : la conclusion n'en exigera pas")
    if not (request.university_instructions or "").strip():
        defaults_used.append(
            "consignes de l'établissement non fournies : la structure proposée suit les usages "
            "courants et n'est présentée comme une règle d'établissement dans aucun cas")

    return {
        "needs_clarification": bool(blockers),
        "questions": questions,
        "defaults_used": defaults_used,
        "blockers": blockers,
    }
