"""Campagne d'orchestration : ouvrir l'étape courante, enregistrer sa proposition, décider.

Trois principes non négociables :
1. **Une seule étape ouverte à la fois** — l'étape courante du parcours, jamais une autre ;
2. le **quota** est consommé AVANT l'appel à l'agent (refuser après coup ne protège rien) ;
3. le statut « validée » ne vient **que** d'une décision humaine (`accepted`).
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from ..core.config import Settings
from ..core.errors import EtatErreur, OrchestratorError
from ..storage import state
from . import call_agent, handoff, quota, registry

DECISIONS = ("accepted", "modified", "refused")


def ordre(settings: Settings) -> list:
    return [etape.numero for etape in settings.etapes]


def _dossier_ou_erreur(settings: Settings, etudiant: str, session: str) -> dict:
    dossier = state.dossier(settings.state_db, etudiant, session)
    if not dossier:
        raise OrchestratorError(EtatErreur.DOSSIER_INCONNU,
                                "Ce dossier n'existe pas.", f"{etudiant}/{session}")
    return dossier


def _verdict(reponse: dict) -> str:
    """Verdict du vérificateur de l'agent — lu, jamais réécrit."""
    verdict = reponse.get("verifier_status")
    if not verdict:
        verificateur = reponse.get("verifier") or {}
        verdict = verificateur.get("verdict") or verificateur.get("status") or ""
    return str(verdict or "")


def creer_dossier(settings: Settings, etudiant: str, session: str, sujet: str,
                  contexte: dict | None = None) -> dict:
    state.initialiser(settings.state_db)
    state.creer_dossier(settings.state_db, etudiant, session, sujet,
                        json.dumps(contexte or {}, ensure_ascii=False))
    return etat(settings, etudiant, session)


def etat(settings: Settings, etudiant: str, session: str) -> dict:
    """Où en est l'étudiant : étape ouverte, statut, quota restant, avancement détaillé."""
    dossier = _dossier_ou_erreur(settings, etudiant, session)
    numero = state.etape_courante(settings.state_db, etudiant, session, ordre(settings))
    etape = settings.par_numero[numero]
    ligne = state.statut(settings.state_db, etudiant, session, numero) or {}
    return {
        "etudiant": etudiant,
        "session": session,
        "sujet": dossier.get("sujet", ""),
        "etape_ouverte": numero,
        "libelle": etape.libelle,
        "statut": ligne.get("statut", state.STATUT_A_FAIRE),
        "verdict": ligne.get("verdict", ""),
        "decision": ligne.get("decision", ""),
        "commentaire": ligne.get("commentaire", ""),
        "quota_restant": quota.restant(settings.state_db, etudiant, settings.analyses_par_jour),
        "quota_max": settings.analyses_par_jour,
        "avancement": state.journal(settings.state_db, etudiant, session),
        # La carte du parcours est fournie au site : celui-ci affiche les étapes sans avoir à
        # connaître, ni à dupliquer, la liste des étapes et leurs libellés.
        "etapes": [{"numero": item.numero, "libelle": item.libelle} for item in settings.etapes],
    }


def lancer_etape(settings: Settings, etudiant: str, session: str, transport=None,
                 interrogateur=None) -> dict:
    """Lance l'étape OUVERTE : disponibilité, quota, entrée faite de sorties réelles, appel.

    Aucune étape ne peut être choisie par l'appelant : c'est le parcours qui décide laquelle est
    ouverte. Une proposition déjà en attente de décision n'est pas recalculée.
    """
    dossier = _dossier_ou_erreur(settings, etudiant, session)
    numero = state.etape_courante(settings.state_db, etudiant, session, ordre(settings))
    etape = settings.par_numero[numero]
    ligne = state.statut(settings.state_db, etudiant, session, numero) or {}
    if ligne.get("statut") == state.STATUT_PROPOSEE:
        raise OrchestratorError(
            EtatErreur.ETAPE_NON_AUTORISEE,
            "Cette étape attend déjà ta décision : valide-la ou demande une révision.",
            f"étape {numero} déjà proposée")

    # L'orchestrateur INTERROGE l'agent avant de lui confier du travail (leçon du lab) : mieux
    # vaut refuser proprement que laisser échouer l'appel avec une erreur technique.
    if transport is None or interrogateur is not None:
        fiche = registry.fiche_de_etape(settings, numero, interrogateur=interrogateur)
        if fiche and not fiche["en_ligne"]:
            raise OrchestratorError(
                EtatErreur.AGENT_INDISPONIBLE,
                "Le service de cette étape est éteint pour le moment. Ton dossier est conservé : "
                "tu pourras relancer l'étape dès qu'il sera rallumé.",
                f"agent « {fiche['agent']} » hors ligne sur {fiche['adresse']}"
                + (f" — {fiche['probleme']}" if fiche.get("probleme") else ""))

    sorties = handoff.sorties_validees(settings, settings.state_db, etudiant, session, etape)
    entree = handoff.construire_entree(settings, etudiant, session, etape, dossier, sorties)

    quota.consommer(settings.state_db, etudiant, settings.analyses_par_jour)
    try:
        reponse = call_agent.appeler(etape.url_analyse(settings.hote), entree,
                                     settings.timeout, transport)
    except OrchestratorError as erreur:
        state.enregistrer_echec(settings.state_db, etudiant, session, numero, erreur.detail)
        raise

    resultat = reponse.get("output") or reponse or {}
    verdict = _verdict(reponse)
    state.enregistrer_resultat(settings.state_db, etudiant, session, numero,
                               resultat, verdict)
    return {
        "etape": numero,
        "libelle": etape.libelle,
        "statut": state.STATUT_PROPOSEE,
        "verdict": verdict,
        "resultat": resultat,
        "quota_restant": quota.restant(settings.state_db, etudiant, settings.analyses_par_jour),
    }


def decider(settings: Settings, etudiant: str, session: str, decision: str,
            commentaire: str = "", transport=None) -> dict:
    """Enregistre la DÉCISION HUMAINE — seule voie d'accès à l'étape suivante."""
    if decision not in DECISIONS:
        raise OrchestratorError(
            EtatErreur.DECISION_INVALIDE,
            "Décision inconnue : attends-toi à « accepted », « modified » ou « refused ».",
            f"décision reçue : {decision!r}")

    numero = state.etape_courante(settings.state_db, etudiant, session, ordre(settings))
    etape = settings.par_numero[numero]
    ligne = state.statut(settings.state_db, etudiant, session, numero) or {}
    if ligne.get("statut") != state.STATUT_PROPOSEE:
        raise OrchestratorError(
            EtatErreur.ETAPE_NON_AUTORISEE,
            "Aucune proposition n'attend ta décision pour cette étape.",
            f"étape {numero} au statut {ligne.get('statut', 'inconnu')!r}")

    avertissement = ""
    try:
        call_agent.appeler(etape.url_decision(settings.hote, etudiant, session),
                           {"decision": decision}, settings.timeout, transport)
    except OrchestratorError as erreur:
        # L'agent n'a pas pu consigner la décision : on le DÉCLARE, on ne le cache pas. La
        # progression reste fondée sur l'état de l'orchestrateur, seule référence du parcours.
        avertissement = ("La décision n'a pas pu être transmise à l'agent de cette étape "
                         f"({erreur.etat.value}) ; elle est enregistrée ici, mais son dossier "
                         "interne peut diverger.")

    statut = state.enregistrer_decision(settings.state_db, etudiant, session, numero,
                                        decision, commentaire)
    etat_dossier = etat(settings, etudiant, session)
    return {
        "etape": numero,
        "libelle": etape.libelle,
        "decision": decision,
        "statut": statut,
        "etape_suivante": etat_dossier["etape_ouverte"],
        "libelle_suivant": etat_dossier["libelle"],
        "avertissement": avertissement,
    }


# ==========================================================================================
# Ce que le SITE a besoin de lire : le détail d'une étape, et les documents de l'étudiant.
# L'orchestrateur reste la seule porte : le site ne connaît ni les agents, ni le stockage.
# ==========================================================================================

# Phrases affichées pour le verdict du vérificateur de l'étape — le verdict lui-même n'est
# jamais réécrit, seulement EXPLIQUÉ.
VERDICTS = {
    "verified": "Un contrôle indépendant a examiné cette proposition : rien n'a été contesté.",
    "validated": "Un contrôle indépendant a examiné cette proposition : rien n'a été contesté.",
    "corrected": "Un contrôle indépendant a examiné cette proposition et a signalé des points à "
                 "corriger ; ils figurent ci-contre.",
    "provisional": "Le contrôle est partiel : certains éléments n'ont pas pu être vérifiés.",
    "verification_failed": "Le contrôle indépendant n'a pas pu aboutir : lisez cette proposition "
                          "avec une attention particulière.",
    "rejected": "Le contrôle de cette étape a émis des réserves sur cette proposition : elles sont "
                "listées ci-contre. C'est à vous de juger, en connaissance de cause.",
    "echec": "L'étape n'a pas abouti.",
}


def _textes(valeur) -> list:
    """Aplatit n'importe quelle valeur en phrases affichables (jamais un objet brut à l'écran)."""
    if valeur is None or valeur == "" or valeur == [] or valeur == {}:
        return []
    if isinstance(valeur, str):
        return [valeur.strip()] if valeur.strip() else []
    if isinstance(valeur, dict):
        for cle in ("texte", "message", "question", "description", "libelle", "label", "constat",
                    "manque", "point", "concerne", "resume"):
            if isinstance(valeur.get(cle), str) and valeur[cle].strip():
                return [valeur[cle].strip()]
        return [f"{cle.replace('_', ' ')} : {valeur[cle]}" for cle in sorted(valeur)
                if isinstance(valeur[cle], (str, int, float)) and str(valeur[cle]).strip()]
    if isinstance(valeur, (list, tuple, set)):
        textes = []
        for element in valeur:
            textes.extend(_textes(element))
        return textes
    return [str(valeur)]


def _chercher(resultat: dict, *cles) -> list:
    """Récupère les premiers champs présents parmi des noms possibles (les agents nomment
    parfois différemment, le site doit afficher sans rien inventer)."""
    for cle in cles:
        if isinstance(resultat, dict) and cle in resultat:
            return _textes(resultat[cle])
    return []


def etape_detail(settings: Settings, etudiant: str, session: str,
                 numero: int | None = None) -> dict:
    """L'étape telle que l'étudiant doit la voir : sa proposition, ses inconnues, ses limites,
    ses questions, et le verdict de vérification — tel quel."""
    _dossier_ou_erreur(settings, etudiant, session)
    ouverte = state.etape_courante(settings.state_db, etudiant, session, ordre(settings))
    numero = int(numero) if numero else ouverte
    if numero not in settings.par_numero:
        raise OrchestratorError(EtatErreur.ETAPE_INCONNUE, "Cette étape n'existe pas.",
                                f"étape {numero} hors parcours")
    if numero > ouverte:
        raise OrchestratorError(
            EtatErreur.ETAPE_NON_AUTORISEE,
            "Cette étape n'est pas encore ouverte : validez d'abord les précédentes.",
            f"étape {numero} demandée alors que l'étape ouverte est {ouverte}")

    etape = settings.par_numero[numero]
    ligne = state.statut(settings.state_db, etudiant, session, numero) or {}
    resultat = state.sortie_proposee(settings.state_db, etudiant, session, numero) or {}
    verdict = ligne.get("verdict", "")
    signalements = _chercher(resultat, "verification_flags", "signalements", "flags", "concerns")
    if not signalements:
        for cle in ("verification_result", "verificateur", "verifier"):
            verification = resultat.get(cle)
            if isinstance(verification, dict):
                signalements = _chercher(verification, "flags", "signalements", "problemes",
                                         "problems", "concerns")
                if signalements:
                    break
    return {
        "numero": numero,
        "libelle": etape.libelle,
        # `position` = rang dans le parcours (1..12) ; `numero` = identifiant interne, qui saute
        # 12 (étape réservée). C'est la POSITION que l'étudiant doit lire : sinon la dernière
        # étape s'afficherait « étape 13 sur 12 ».
        "position": ordre(settings).index(numero) + 1,
        "total_etapes": len(settings.etapes),
        "statut": ligne.get("statut", state.STATUT_A_FAIRE),
        "ouverte": numero == ouverte,
        "verdict": verdict,
        "verdict_texte": VERDICTS.get(str(verdict).lower(), ""),
        "resultat": resultat,
        "inconnues": _chercher(resultat, "unknowns", "missing_information", "identified_unknowns",
                               "identified_gaps", "informations_manquantes"),
        "limites": _chercher(resultat, "limits_of_this_output", "limites", "limits",
                             "identified_limits", "limites_identifiees"),
        "questions": _chercher(resultat, "questions_for_human", "questions",
                               "questions_for_student", "clarification_questions"),
        "signalements": signalements,
    }


# ---------------------------------------------------------- documents & bibliographie
AGENT_DOCUMENTAIRE = "literature_review_agent"


def _etape_documentaire(settings: Settings):
    for etape in settings.etapes:
        if etape.agent == AGENT_DOCUMENTAIRE:
            return etape
    return None


def _lire_agent(settings: Settings, chemin: str, transport=None) -> bytes:
    """Lecture seule chez l'agent documentaire. Aucun calcul, aucun quota consommé."""
    etape = _etape_documentaire(settings)
    if etape is None:
        raise OrchestratorError(EtatErreur.ETAPE_INCONNUE,
                                "Les documents ne sont pas disponibles sur cette plateforme.",
                                "aucune étape documentaire dans la carte")
    url = f"http://{settings.hote}:{etape.port}{chemin}"
    if transport is not None:
        return transport(url)
    requete = urllib.request.Request(url, headers={"Accept": "*/*"})
    try:
        with urllib.request.urlopen(requete, timeout=settings.timeout) as reponse:
            return reponse.read()
    except urllib.error.HTTPError as erreur:
        if erreur.code == 404:
            raise OrchestratorError(
                EtatErreur.DOSSIER_INCONNU,
                "Aucun document n'est encore disponible pour ce mémoire.",
                f"HTTP 404 sur {url}") from erreur
        raise OrchestratorError(
            EtatErreur.AGENT_INDISPONIBLE,
            "Le service des documents est éteint pour le moment. Réessayez plus tard.",
            f"HTTP {erreur.code} sur {url}") from erreur
    except (urllib.error.URLError, OSError, TimeoutError) as erreur:
        raise OrchestratorError(
            EtatErreur.AGENT_INDISPONIBLE,
            "Le service des documents ne répond pas pour le moment. Réessayez plus tard.",
            f"{type(erreur).__name__} sur {url}") from erreur


def documents(settings: Settings, etudiant: str, session: str, transport=None) -> dict:
    """Manifeste NORMALISÉ : le site n'a pas à connaître le format interne de l'agent."""
    _dossier_ou_erreur(settings, etudiant, session)
    reference = (f"/literature/{urllib.parse.quote(etudiant, safe='')}"
                 f"/{urllib.parse.quote(session, safe='')}/documents")
    brut = json.loads(_lire_agent(settings, reference, transport) or b"{}")
    entrees = []
    for entree in brut.get("entries", []):
        auteurs = entree.get("authors") or entree.get("auteurs") or []
        if isinstance(auteurs, str):
            auteurs = [auteurs]
        liste = [str(auteur) for auteur in auteurs if str(auteur).strip()]
        texte_auteurs = ", ".join(liste[:4]) + (" et al." if len(liste) > 4 else "")
        doi = entree.get("doi") or ""
        entrees.append({
            "doc_id": str(entree.get("doc_id", "")),
            "titre": entree.get("title") or entree.get("titre") or "Sans titre",
            "auteurs": texte_auteurs or "Auteurs non renseignés",
            "annee": entree.get("year") or entree.get("annee") or "",
            "revue": entree.get("venue") or entree.get("journal") or entree.get("revue") or "",
            "lien": entree.get("url_source") or (f"https://doi.org/{doi}" if doi else ""),
            "telechargeable": bool(entree.get("downloaded") and entree.get("file_name")),
        })
    return {
        "entries": entrees,
        "resume": {"references": len(entrees),
                   "telecharges": sum(1 for e in entrees if e["telechargeable"])},
    }


def fichier_document(settings: Settings, etudiant: str, session: str, doc_id: str,
                     transport=None) -> bytes:
    _dossier_ou_erreur(settings, etudiant, session)
    reference = (f"/literature/{urllib.parse.quote(etudiant, safe='')}"
                 f"/{urllib.parse.quote(session, safe='')}/documents/"
                 f"{urllib.parse.quote(str(doc_id), safe='')}/file")
    return _lire_agent(settings, reference, transport)


def bibliographie(settings: Settings, etudiant: str, session: str, format: str = "bibtex",
                  transport=None) -> bytes:
    """Export bibliographique — recopie pure de ce que l'agent a réellement collecté."""
    _dossier_ou_erreur(settings, etudiant, session)
    format = format if format in ("bibtex", "ris", "csv") else "bibtex"
    reference = (f"/literature/{urllib.parse.quote(etudiant, safe='')}"
                 f"/{urllib.parse.quote(session, safe='')}/bibliographie?format={format}")
    return _lire_agent(settings, reference, transport)
