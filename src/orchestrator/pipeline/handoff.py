"""Pont entre étapes : la sortie RÉELLE d'une étape devient l'entrée de la suivante.

Leçon du projet (bug réel) : un décalage de structure entre deux agents passe INAPERÇU, car les
schémas d'entrée tolèrent des champs en trop. On ne transmet donc **jamais** un payload fabriqué à
la main : uniquement ce qu'une étape a réellement produit, et si une sortie manque, on ÉCHOUE au
lieu de présenter une entrée incomplète comme complète.
"""

from ..core.config import Etape, Settings
from ..core.errors import EtatErreur, OrchestratorError

# Intitulés lisibles employés quand un champ collecté par le site doit être recopié dans un champ
# de contexte libre, faute d'être accepté tel quel par l'agent de l'étape.
LIBELLES_CONTEXTE = {
    "subject_text": "sujet du mémoire",
    "discipline": "discipline",
    "academic_level": "niveau d'études",
    "country": "pays",
    "institution": "établissement",
    "geographical_scope": "zone géographique",
    "period": "période étudiée",
    "research_problem": "problème observé",
    "prior_work": "travaux déjà réalisés",
    "additional_constraints": "contraintes particulières",
}


def construire_entree(settings: Settings, etudiant: str, session: str, etape: Etape,
                      dossier: dict | None, sorties: dict) -> dict:
    """Assemble l'entrée de l'agent pour `etape`.

    `sorties` : {numéro d'étape: sortie réelle validée}. Toute sortie attendue qui manque fait
    échouer la préparation — l'étape ne peut pas démarrer sur un dossier incomplet.
    """
    if not dossier:
        raise OrchestratorError(
            EtatErreur.DOSSIER_INCONNU,
            "Ce dossier n'existe pas : impossible de préparer l'étape.",
            f"dossier inconnu pour {etudiant}/{session}")

    entree: dict = {"student_id": etudiant, "session_id": session or ""}

    # Champs de base déclarés en configuration (jamais devinés) : le sujet vient du dossier,
    # les autres sont ceux que l'étudiant a réellement fournis au moment de créer le dossier.
    contexte = dossier.get("contexte") or {}
    if isinstance(contexte, str):
        try:
            import json
            contexte = json.loads(contexte) if contexte else {}
        except (TypeError, ValueError):
            contexte = {}
    sujet = (dossier.get("sujet") or "").strip()

    # Champs de base transmis à CETTE étape : sa propre TABLE DE CORRESPONDANCE si elle en déclare
    # une, sinon la correspondance identité de la liste globale. Un champ absent de la table n'est
    # JAMAIS envoyé — l'agent le refuserait (422 « Extra inputs are not permitted ») ; il est
    # recopié plus bas, avec son intitulé, dans le champ de contexte libre de l'agent.
    if etape.champs:
        correspondance = dict(etape.champs)
    else:
        correspondance = {champ: champ for champ in settings.champs_base}

    non_acceptes: list[str] = []
    for champ in settings.champs_base:
        if champ in ("student_id", "session_id"):
            continue
        valeur = contexte.get(champ)
        if champ not in correspondance:
            if valeur not in (None, "", [], {}):
                non_acceptes.append(champ)
            continue
        attendu = correspondance[champ]
        if champ == "subject_text":
            if sujet:
                entree[attendu] = sujet
        elif valeur not in (None, "", [], {}):
            entree[attendu] = valeur

    # Les champs que cet agent n'accepte PAS ne sont pas perdus : quand l'agent prévoit un champ de
    # contexte libre, ils y sont RECOPIÉS tels quels, avec leur intitulé lisible. On ne devine rien
    # et on n'écarte aucune information fournie par l'étudiant.
    if etape.contexte_libre and non_acceptes and not entree.get(etape.contexte_libre):
        entree[etape.contexte_libre] = "\n".join(
            f"{LIBELLES_CONTEXTE.get(champ, champ.replace('_', ' '))} : {contexte[champ]}"
            for champ in non_acceptes)

    # Pont : la sortie réelle de chaque étape amont, sous le nom de champ attendu par l'agent.
    for champ, source in etape.upstream.items():
        sortie = sorties.get(source)
        if sortie is None:
            raise OrchestratorError(
                EtatErreur.SORTIE_AMONT_MANQUANTE,
                f"L'étape {source} doit être validée avant de pouvoir lancer l'étape "
                f"« {etape.libelle} ».",
                f"sortie validée de l'étape {source} absente")
        entree[champ] = sortie
    return entree


def sorties_validees(settings: Settings, chemin_etat, etudiant: str, session: str,
                     etape: Etape) -> dict:
    """Sorties VALIDÉES des étapes amont, telles qu'enregistrées (aucune transformation)."""
    from ..storage import state

    sorties: dict = {}
    for source in sorted(set(etape.upstream.values())):
        sortie = state.sortie_validee(chemin_etat, etudiant, session, source)
        if sortie is not None:
            sorties[source] = sortie
    return sorties
