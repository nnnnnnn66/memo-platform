"""Pré-cadrage (SPEC §5, §14) : une analyse peut-elle être conduite ?

Déterministe. Le cadre est la MÉTHODOLOGIE VALIDÉE de l'étape 9. Sans données exploitables, l'agent ne
produit AUCUN résultat : il propose un plan d'analyse et dit ce qui manque (chemin STOP de la SPEC).
"""


def check(request) -> dict:
    blockers: list[str] = []
    questions: list[str] = []

    methodology = request.upstream_methodology
    if methodology is None:
        blockers.append("la méthodologie validée de l'étape 9")
        questions.append(
            "Pouvez-vous transmettre la méthodologie validée (étape 9, avec le verdict du vérificateur "
            "et votre décision) ? Sans elle, aucun traitement ni analyse ne peut être justifié.")
    else:
        if not methodology.is_verified:
            blockers.append("une méthodologie dont le vérificateur a validé le contenu")
            questions.append(
                "La méthodologie transmise n'est pas marquée vérifiée. Finalisez l'étape 9 (vérificateur "
                "puis décision), ou confirmez explicitement votre validation.")
        status = request.methodology_status()
        if status not in ("valide", "en_attente_de_validation"):
            blockers.append("une méthodologie au statut « validé » ou « en attente de validation »")
            questions.append(
                f"Le statut de la méthodologie est « {status or 'inconnu'} ». Une méthodologie "
                "provisoire ne peut pas fonder une analyse de résultats.")

    if not request.effective_subject().strip():
        blockers.append("le sujet exact du mémoire")
        questions.append("Pouvez-vous préciser le sujet exact du mémoire ?")

    if not request.effective_question().strip():
        blockers.append("la question de recherche principale")
        questions.append("Pouvez-vous transmettre la question de recherche principale validée ?")

    defaults_used: list[str] = []
    if not request.has_data():
        defaults_used.append(
            "aucune donnée exploitable fournie : l'agent produira un PLAN D'ANALYSE et la liste des "
            "données nécessaires — aucun résultat ne sera produit")
    if not (request.data_origin or "").strip():
        defaults_used.append("origine des données non précisée : provenance à confirmer")
    if not (request.data_period or "").strip():
        defaults_used.append("période des données non précisée : périmètre à confirmer")
    if request.hypotheses_not_required():
        defaults_used.append(
            "l'étape 7 a conclu qu'aucune hypothèse n'est pertinente : aucune hypothèse ne sera "
            "examinée")

    return {
        "needs_clarification": bool(blockers),
        "questions": questions,
        "defaults_used": defaults_used,
        "blockers": blockers,
    }
