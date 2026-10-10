"""Pré-cadrage (SPEC §5, §14) : un audit transversal a-t-il un sens sur ce dossier ?"""

from ..analysis import coherence_rules


def check(request) -> dict:
    dossier = coherence_rules.etat_du_dossier(request)
    blockers: list[str] = []
    questions: list[str] = []

    if not dossier.exploitable:
        blockers.append("au moins deux étapes exploitables")
        questions.append(
            "Le dossier ne contient que "
            f"{len(dossier.etapes_presentes)} étape(s) : une confrontation transversale n'a pas de "
            "sens. Transmettez les sorties validées des étapes précédentes.")
    if not request.effective_subject().strip():
        blockers.append("le sujet exact du mémoire")
        questions.append("Pouvez-vous préciser le sujet exact du mémoire ?")
    if not request.effective_question().strip():
        blockers.append("la question de recherche")
        questions.append(
            "Pouvez-vous transmettre la question de recherche validée ? Sans elle, les objectifs, le "
            "dispositif et la conclusion ne peuvent pas être confrontés.")
    if dossier.etapes_absentes and len(dossier.etapes_absentes) > 6:
        questions.append(
            "De nombreuses étapes ne sont pas transmises (" +
            ", ".join(dossier.etapes_absentes[:8]) +
            ") : l'audit sera partiel et le déclarera.")

    defaults_used: list[str] = []
    if dossier.etapes_absentes:
        defaults_used.append(
            f"audit PARTIEL : {len(dossier.etapes_absentes)} étape(s) absente(s) — les liens qui en "
            "dépendent sont déclarés non examinés")
    if dossier.etapes_non_verifiees:
        defaults_used.append(
            f"{len(dossier.etapes_non_verifiees)} étape(s) non vérifiée(s) : l'audit porte sur des "
            "contenus non contrôlés, et le rapport le signale")
    if not (request.university_instructions or "").strip():
        defaults_used.append(
            "consignes de l'établissement non fournies : leur conformité est déclarée NON VÉRIFIABLE, "
            "jamais jugée")

    return {
        "needs_clarification": bool(blockers),
        "questions": questions,
        "defaults_used": defaults_used,
        "blockers": blockers,
        "dossier": dossier,
    }
