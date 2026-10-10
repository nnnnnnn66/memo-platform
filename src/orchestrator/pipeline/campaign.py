"""Campagne d'orchestration : ouvrir l'étape courante, enregistrer sa proposition, décider.

Trois principes non négociables :
1. **Une seule étape ouverte à la fois** — l'étape courante du parcours, jamais une autre ;
2. le **quota** est consommé AVANT l'appel à l'agent (refuser après coup ne protège rien) ;
3. le statut « validée » ne vient **que** d'une décision humaine (`accepted`).
"""

import json

from ..core.config import Settings
from ..core.errors import EtatErreur, OrchestratorError
from ..storage import state
from . import call_agent, handoff, quota

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
    }


def lancer_etape(settings: Settings, etudiant: str, session: str, transport=None) -> dict:
    """Lance l'étape OUVERTE : quota, entrée faite de sorties réelles, appel, enregistrement.

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
