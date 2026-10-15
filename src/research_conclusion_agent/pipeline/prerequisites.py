"""Pré-cadrage (SPEC §5, §14) : une conclusion peut-elle être rédigée ?

Déterministe. Le point de départ est constitué des éléments VALIDÉS des étapes précédentes — en
particulier les résultats VÉRIFIÉS de l'étape 10. Sans eux, la conclusion se limite à un PLAN.
"""


def check(request) -> dict:
    blockers: list[str] = []
    questions: list[str] = []

    # L'état des résultats de l'étape 10 n'est PAS un prérequis BLOQUANT : sans résultat exploitable,
    # la production devient un PLAN de conclusion (voir `_assemble`, qui le déclare et n'invente
    # rien). Défaut réel constaté en simulation complète : un dossier mené jusqu'au bout se voyait
    # renvoyé en arrière (« le statut des résultats est brouillon ») à la DERNIÈRE étape — l'étudiante
    # restait bloquée sur une demande qui ne dépend pas d'elle (les résultats de terrain n'existent
    # pas encore). Consigne du porteur, PRIORITAIRE : un agent LIVRE, il ne renvoie pas l'étudiant à
    # sa copie. Seule l'absence TOTALE de l'étape 10 reste signalée, et la production d'un plan
    # lorsqu'aucun résultat n'est exploitable est désormais DÉCLARÉE dans les limites.
    if request.upstream_results is None:
        defaults_used_note = ("les résultats de l'étape 10 n'ont pas été transmis : la production se "
                              "limitera à un PLAN de conclusion et aux informations à recueillir")
    else:
        defaults_used_note = ""

    if not request.effective_question().strip():
        blockers.append("la question de recherche principale")
        questions.append("Pouvez-vous transmettre la question de recherche principale validée ? La "
                         "conclusion doit y répondre explicitement.")
    if not request.effective_subject().strip():
        blockers.append("le sujet exact du mémoire")
        questions.append("Pouvez-vous préciser le sujet exact du mémoire ?")

    defaults_used: list[str] = []
    if defaults_used_note:
        defaults_used.append(defaults_used_note)
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
