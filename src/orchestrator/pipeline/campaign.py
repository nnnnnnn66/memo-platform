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

from ..core import routage
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


def detail_du_verificateur(reponse: dict) -> dict | None:
    """Le détail du vérificateur de l'étape, transporté TEL QUEL (jamais interprété).

    Une étape non vérifiée doit pouvoir dire POURQUOI : quelles corrections ont été demandées, et
    sur quel motif. Jeter ce détail rendait l'échec inexplicable pour l'étudiant comme pour nous.
    """
    verificateur = reponse.get("verifier") or reponse.get("verificateur") or {}
    if not verificateur:
        return None
    return {
        "verdict": str(verificateur.get("verdict") or verificateur.get("status") or ""),
        "corrections": list(verificateur.get("corrections") or []),
        "motif": (verificateur.get("motif") or verificateur.get("reason")
                  or verificateur.get("justification") or ""),
    }


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
                                     (etape.timeout or settings.timeout), transport)
    except OrchestratorError as erreur:
        state.enregistrer_echec(settings.state_db, etudiant, session, numero, erreur.detail)
        raise

    resultat = reponse.get("output") or reponse or {}
    verdict = _verdict(reponse)
    state.enregistrer_resultat(settings.state_db, etudiant, session, numero,
                               resultat, verdict)

    # POURQUOI une vérification a échoué. Le vérificateur de l'agent produit ses exigences
    # (corrections demandées, motif) ; l'orchestrateur les JETAIT. Résultat : un étudiant lisait
    # « le contrôle indépendant n'a pas pu aboutir » sans aucune raison, et personne ne pouvait
    # savoir ce qui bloquait — constaté en répétition générale sur un sujet neuf.
    detail_verificateur = detail_du_verificateur(reponse)

    reponse_finale = {
        "etape": numero,
        "libelle": etape.libelle,
        "statut": state.STATUT_PROPOSEE,
        "verdict": verdict,
        "resultat": resultat,
        "verificateur": detail_verificateur,
        "quota_restant": quota.restant(settings.state_db, etudiant, settings.analyses_par_jour),
        "decision_automatique": False,
        "etape_suivante": None,
    }

    # CONSIGNE DU PORTEUR : la plateforme tourne EN LIGNE et ne doit pas attendre une validation
    # pour avancer. Une étape produite ET VÉRIFIÉE par son propre vérificateur ouvre donc la
    # suivante immédiatement. Le vérificateur indépendant est la barrière de qualité ; la décision
    # humaine reste POSSIBLE (le site peut demander une révision), elle n'est plus OBLIGATOIRE.
    #
    # On n'avance JAMAIS sur une production non vérifiée : les étapes suivantes la refuseraient, et
    # la chaîne s'arrêterait plus loin — c'est exactement ce qui s'est produit lors du premier
    # parcours réel. Non vérifiée = on s'arrête là et on le dit.
    if settings.validation_automatique and verdict.lower() == "verified":
        state.enregistrer_decision(settings.state_db, etudiant, session, numero, "accepted",
                                   "validation automatique (mode en ligne)")
        suivante = state.etape_courante(settings.state_db, etudiant, session, ordre(settings))
        reponse_finale["decision_automatique"] = True
        reponse_finale["etape_suivante"] = suivante if suivante != numero else None
    return reponse_finale


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
    # Une proposition NON vérifiée peut être validée (la décision humaine reste souveraine), mais
    # pas en silence : l'étape suivante refusera de s'appuyer dessus. Défaut réel — un parcours
    # automatique a validé une proposition vide, et l'étape suivante s'est arrêtée sur
    # « la sortie transmise n'est pas vérifiée ».
    if decision == "accepted" and str(ligne.get("verdict", "")).lower() not in ("verified",):
        avertissement = (
            "Attention : cette proposition n'a PAS été vérifiée"
            + (f" (verdict « {ligne.get('verdict')} »)" if ligne.get("verdict") else "")
            + ". L'étape suivante refusera probablement de s'appuyer dessus : relis d'abord ce "
              "qu'elle te demande.")
    try:
        call_agent.appeler(etape.url_decision(settings.hote, etudiant, session),
                           {"decision": decision}, (etape.timeout or settings.timeout), transport)
    except OrchestratorError as erreur:
        # Un agent qui n'expose PAS de route de décision renvoie 404. Ce n'est pas une panne : tous
        # les agents ne sont pas concernés par la décision de l'étudiant, et l'orchestrateur reste
        # la référence du parcours (il a déjà enregistré la décision avant d'appeler). Le dire comme
        # un incident faisait croire à un dossier divergent — défaut relevé en exécution réelle.
        if "HTTP 404" in (erreur.detail or ""):
            avertissement = ""
        else:
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
# REPRENDRE UNE ÉTAPE DÉJÀ FRANCHIE
# ==========================================================================================
# MANQUE COMBLÉ : une étape validée était définitive. Pour revenir dessus, il fallait intervenir
# directement dans la base SQLite — or un mémoire est ITÉRATIF : l'étudiant reçoit de nouvelles
# données, ou veut corriger une étape. Une plateforme en ligne doit le permettre.
#
# COMPORTEMENT CHOISI, ET POURQUOI (le point le plus délicat)
# ----------------------------------------------------------
# Reprendre une étape rouvre l'étape, ET invalide ses étapes AVAL (elles passent `a_reviser`).
#
# Pourquoi invalider plutôt que « simplement signaler » : on ne peut pas savoir À L'AVANCE si la
# nouvelle production différera de l'ancienne. Tant qu'elle n'a pas été rejouée et vérifiée, les
# étapes qui s'appuyaient dessus reposent FACTUELLEMENT sur une version antérieure. Les laisser
# `validee` les ferait mentir en silence : elles seraient transmises à leurs propres étapes aval
# comme si elles avaient été bâties sur la version courante. Ici :
#   - leur PRODUCTION est CONSERVÉE (rien n'est effacé : l'étudiant peut la relire) ;
#   - leur STATUT cesse d'être `validee`, donc `sortie_validee` refuse de la transmettre
#     (le contrat `upstream_*` ne peut plus être satisfait par une version périmée) ;
#   - `etape_detail` DIT pourquoi (`repose_sur`) : « cette étape repose sur une version antérieure
#     de l'étape N ».
# Le parcours reste donc cohérent : l'étape reprise est la première non validée (elle est ouverte),
# et les étapes aval se rejouent, dans l'ORDRE DU PARCOURS, après elle.
#
# La contrainte « on n'avance JAMAIS sur une production non vérifiée » est intacte : la reprise ne
# valide rien. Elle rouvre — c'est le verdict du vérificateur du nouveau passage (mode automatique)
# ou la décision de l'étudiant qui refermera l'étape, exactement comme au premier passage.
#
# Les décisions déjà prises restent traçables : elles sont journalisées dans `reprises` AVANT que
# la ligne ne soit réécrite (le nouveau passage remet `decision`/`commentaire` à zéro).

def etapes_aval(settings: Settings, numero: int) -> list:
    """Étapes du parcours qui dépendent, DIRECTEMENT OU NON, de `numero` — dans l'ordre du parcours.

    La dépendance vient du contrat réel (`upstream`) : une étape qui relit la sortie d'une étape
    aval invalide est aval elle aussi, transitivement.
    """
    dependants: set = set()
    progression = True
    while progression:
        progression = False
        for etape in settings.etapes:
            if etape.numero == numero or etape.numero in dependants:
                continue
            amont = set(etape.upstream.values())
            if numero in amont or (amont & dependants):
                dependants.add(etape.numero)
                progression = True
    return [n for n in ordre(settings) if n in dependants]


def reprendre(settings: Settings, etudiant: str, session: str, numero: int) -> dict:
    """Rouvre une étape DÉJÀ FRANCHIE et invalide ses étapes aval.

    Refusés, et dits clairement : un dossier inconnu, une étape hors parcours, une étape jamais
    atteinte, et une étape qui n'est pas franchie (déjà ouverte, ou en attente de décision : la
    relancer est déjà possible, la « reprendre » serait un doublon silencieux).
    """
    _dossier_ou_erreur(settings, etudiant, session)
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        raise OrchestratorError(EtatErreur.ETAPE_INCONNUE, "Cette étape n'existe pas.",
                                f"étape {numero!r} illisible")

    if numero not in settings.par_numero:
        raise OrchestratorError(EtatErreur.ETAPE_INCONNUE, "Cette étape n'existe pas.",
                                f"étape {numero} hors parcours")

    etape = settings.par_numero[numero]
    ligne = state.statut(settings.state_db, etudiant, session, numero) or {}
    statut = ligne.get("statut", state.STATUT_A_FAIRE)

    # Jamais atteinte : aucune trace de production (colonne absente = jamais lancée).
    if not ligne or statut == state.STATUT_A_FAIRE:
        raise OrchestratorError(
            EtatErreur.ETAPE_NON_AUTORISEE,
            f"Tu n'as pas encore franchi l'étape « {etape.libelle} » : il n'y a rien à reprendre.",
            f"étape {numero} jamais atteinte (statut {statut!r})")

    # Pas (encore) franchie : elle est ouverte, ou attend une décision — la relancer est déjà le
    # geste normal, une « reprise » serait ambiguë et ferait perdre la proposition en cours.
    if statut != state.STATUT_VALIDEE:
        raise OrchestratorError(
            EtatErreur.ETAPE_NON_AUTORISEE,
            f"L'étape « {etape.libelle} » n'est pas franchie : elle est déjà ouverte. "
            "Relance-la (ou décide-la) : il n'y a rien à rouvrir.",
            f"étape {numero} au statut {statut!r}")

    aval = etapes_aval(settings, numero)
    motif = f"reprise de l'étape {numero} par l'étudiant"

    # On ne « revoit » que les étapes réellement atteintes : les suivantes n'ont aucune production à
    # revoir (elles sont encore `a_faire`) — les annoncer ne serait que du bruit.
    def _atteinte(n: int) -> bool:
        ligne_aval = state.statut(settings.state_db, etudiant, session, n) or {}
        return bool(ligne_aval) and ligne_aval.get("statut") != state.STATUT_A_FAIRE

    aval_atteintes = [n for n in aval if _atteinte(n)]

    # Journaliser AVANT de réécrire : c'est ce qui garde la décision antérieure traçable.
    state.enregistrer_reprise(settings.state_db, etudiant, session, numero,
                              dict(ligne), aval_atteintes, motif)
    state.rouvrir(settings.state_db, etudiant, session, numero)
    for suivant in aval_atteintes:
        state.marquer_a_reviser(settings.state_db, etudiant, session, suivant)

    etat_dossier = etat(settings, etudiant, session)
    return {
        "etape": numero,
        "libelle": etape.libelle,
        "statut": state.STATUT_A_FAIRE,
        "reprise": True,
        "etape_ouverte": etat_dossier["etape_ouverte"],
        "libelle_ouvert": etat_dossier["libelle"],
        "ancien_statut": ligne.get("statut", ""),
        "ancien_verdict": ligne.get("verdict", ""),
        "ancienne_decision": ligne.get("decision", ""),
        "etapes_aval_a_revoir": [
            {"numero": n, "libelle": settings.par_numero[n].libelle} for n in aval_atteintes],
        "message": (
            f"L'étape « {etape.libelle} » est de nouveau ouverte : relance-la quand tu veux. "
            + (f"Les étapes suivantes ({len(aval_atteintes)}) s'appuyaient sur les anciennes "
               "données : elles sont à revoir, et il te sera demandé de les relancer dans l'ordre."
               if aval_atteintes else "Rien d'autre n'en dépend pour l'instant.")),
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


def _repose_sur(settings: Settings, etudiant: str, session: str, etape) -> dict | None:
    """L'étape AMONT encore ouverte dont cette étape dépend — celle qui la fait « reposer sur une
    version antérieure ».

    Après une reprise, les étapes aval cessent d'être `validee` : sans cette explication, l'étudiant
    lirait « à revoir » sans comprendre pourquoi. On renvoie la PREMIÈRE étape amont non validée
    (dans l'ORDRE DU PARCOURS, jamais l'ordre numérique) — c'est elle qui bloque en premier.
    """
    parcours = ordre(settings)
    for source in sorted(etape.upstream.values(),
                         key=lambda n: parcours.index(n) if n in parcours else len(parcours)):
        ligne = state.statut(settings.state_db, etudiant, session, source) or {}
        if ligne.get("statut") != state.STATUT_VALIDEE:
            return {"numero": source,
                    "libelle": settings.par_numero[source].libelle,
                    "statut": ligne.get("statut", state.STATUT_A_FAIRE)}
    return None


def etape_detail(settings: Settings, etudiant: str, session: str,
                 numero: int | None = None) -> dict:
    """L'étape telle que l'étudiant doit la voir : sa proposition, ses inconnues, ses limites,
    ses questions, et le verdict de vérification — tel quel.

    Deux modes, et c'est délibéré :
    - l'étape déjà atteinte : son contenu réel ;
    - l'étape À VENIR : ce qu'elle demandera (`resume`), sans contenu. **Regarder devant n'est pas
      une faute** : on ne cache pas la suite à l'étudiant, sinon il subit le parcours au lieu de
      l'anticiper. Ce qui reste interdit, c'est de la PRODUIRE — c'est `lancer_etape` qui le
      refuse, pas l'affichage.
    """
    _dossier_ou_erreur(settings, etudiant, session)
    ouverte = state.etape_courante(settings.state_db, etudiant, session, ordre(settings))
    numero = int(numero) if numero else ouverte
    if numero not in settings.par_numero:
        raise OrchestratorError(EtatErreur.ETAPE_INCONNUE, "Cette étape n'existe pas.",
                                f"étape {numero} hors parcours")
    parcours = ordre(settings)
    # Comparaison par POSITION, jamais par numéro : le parcours n'est pas numérique (la
    # vérification globale porte le numéro 13 et vient AVANT la conclusion, qui porte le 11).
    # Un `numero > ouverte` se trompait dès que ces deux étapes étaient en jeu — défaut introduit
    # par le réordonnancement voulu par le porteur, corrigé ici.
    #
    # « À venir » veut dire JAMAIS PRODUITE. Après une REPRISE, les étapes aval invalides se
    # trouvent APRÈS l'étape reprise — mais elles EXISTENT : elles reposent sur une version
    # antérieure et doivent rester lisibles, avec leur statut `a_reviser` et l'explication
    # (`repose_sur`). Les renvoyer comme « à venir » les ferait disparaître, et l'étudiant ne
    # comprendrait pas qu'il doit les revoir.
    ligne = state.statut(settings.state_db, etudiant, session, numero) or {}
    atteinte = bool(ligne) and ligne.get("statut") != state.STATUT_A_FAIRE
    if parcours.index(numero) > parcours.index(ouverte) and not atteinte:
        etape = settings.par_numero[numero]
        return {
            "numero": numero,
            "libelle": etape.libelle,
            "position": parcours.index(numero) + 1,
            "total_etapes": len(settings.etapes),
            "statut": state.STATUT_A_FAIRE,
            "ouverte": False,
            "a_venir": True,
            "resume": etape.resume,
            "verdict": "", "verdict_texte": "",
            "resultat": {}, "inconnues": [], "limites": [], "questions": [], "signalements": [],
            "reprises": 0, "historique_reprises": [], "repose_sur": None,
        }

    etape = settings.par_numero[numero]
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
        "a_venir": False,
        "resume": etape.resume,
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
        # Reprise : combien de fois cette étape a été rouverte, son journal (les décisions
        # antérieures y restent lisibles), et — pour une étape AVAL invalidée par une reprise —
        # l'étape amont sur laquelle elle « repose » désormais. On ne se contente pas de marquer
        # « à revoir » : on dit POURQUOI.
        "reprises": len(state.reprises(settings.state_db, etudiant, session, numero)),
        "historique_reprises": state.reprises(settings.state_db, etudiant, session, numero),
        "repose_sur": (None if ligne.get("statut") == state.STATUT_VALIDEE
                       else _repose_sur(settings, etudiant, session, etape)),
    }


MESSAGES_QUESTION = {
    "rattachee_avec_contenu": (
        "Ta question relève de l'étape {position} — {libelle}. "
        "Voici ce que ton dossier contient déjà sur ce point."),
    "rattachee_sans_contenu": (
        "Ta question relève de l'étape {position} — {libelle}, que tu n'as pas encore traitée. "
        "C'est là qu'elle trouvera sa réponse."),
    "non_rattachee": (
        "Je n'ai pas réussi à rattacher ta question à une étape précise. Précise-la — par exemple "
        "« mon échantillon est-il suffisant ? » ou « mes hypothèses tiennent-elles avec ma "
        "méthodologie ? »."),
}

# Clés qui portent, selon l'agent, le texte réellement produit. On les essaie dans l'ordre avant de
# se rabattre sur le texte le plus long trouvé : on restitue ce que l'agent a écrit, jamais un
# résumé inventé par l'orchestrateur.
CLES_SUBSTANCE = ("proposition", "texte_complet", "texte", "synthese", "synthesis", "resume",
                  "summary", "statement", "reformulated", "conclusion", "protocole", "protocol")
LONGUEUR_SUBSTANCE = 40
LONGUEUR_SUBSTANCE_MAX = 1500


def _substance(sortie: dict, profondeur: int = 0) -> str:
    """Le texte que l'agent a produit, restitué TEL QUEL (jamais réécrit par l'orchestrateur)."""
    if not isinstance(sortie, dict) or profondeur > 3:
        return ""
    textes: list[tuple[str, str]] = []

    def _collecter(cle: str, valeur) -> None:
        if isinstance(valeur, str) and len(valeur.strip()) >= LONGUEUR_SUBSTANCE:
            textes.append((cle, valeur.strip()))
        elif isinstance(valeur, dict) and profondeur < 3:
            for sous_cle, sous_valeur in valeur.items():
                _collecter(sous_cle, sous_valeur)
        elif isinstance(valeur, (list, tuple)) and profondeur < 3:
            for element in valeur:
                _collecter(cle, element)

    for cle, valeur in sortie.items():
        _collecter(cle, valeur)

    for cle_preferee in CLES_SUBSTANCE:
        for cle, texte in textes:
            if cle == cle_preferee:
                return texte[:LONGUEUR_SUBSTANCE_MAX]
    if not textes:
        return ""
    return max(textes, key=lambda item: len(item[1]))[1][:LONGUEUR_SUBSTANCE_MAX]


def question(settings: Settings, etudiant: str, session: str, texte: str) -> dict:
    """Question libre de l'étudiant : l'orchestrateur DÉSIGNE l'étape (donc l'agent) qui la porte.

    L'orchestrateur ne répond pas lui-même et ne devine jamais : il rattache la question par un
    vocabulaire fermé (`core.routage`), puis restitue ce que le dossier contient DÉJÀ sur cette
    étape. **Sans effet de bord** : aucun quota consommé, aucune écriture, aucun agent appelé.
    """
    _dossier_ou_erreur(settings, etudiant, session)
    propre = " ".join(str(texte or "").split())
    if len(propre) < routage.LONGUEUR_MINIMALE:
        raise OrchestratorError(EtatErreur.ENTREE_INVALIDE, "Posez une vraie question.",
                                f"question trop courte ({len(propre)} caractères)")
    if len(propre) > routage.LONGUEUR_MAXIMALE:
        raise OrchestratorError(
            EtatErreur.ENTREE_INVALIDE,
            f"Votre question dépasse {routage.LONGUEUR_MAXIMALE} caractères : raccourcissez-la.",
            f"question de {len(propre)} caractères")

    decision = routage.router(propre)
    reponse = {
        "question": propre,
        "etape": None, "position": None, "libelle": None, "agent": None,
        "confiance": decision["confiance"],
        "methode": decision["methode"],
        "indices": decision["indices"],
        "scores": decision["scores"],
        "autres_etapes": [],
        "extrait": None,
        "message": MESSAGES_QUESTION["non_rattachee"],
    }

    principale = decision["principale"]
    if principale is None:
        return reponse

    etape = settings.par_numero[principale]
    parcours = ordre(settings)
    reponse.update({"etape": principale,
                    "position": parcours.index(principale) + 1,
                    "libelle": etape.libelle,
                    "agent": etape.agent})
    reponse["autres_etapes"] = [
        {"numero": numero, "libelle": settings.par_numero[numero].libelle}
        for numero in decision["etapes"] if numero != principale and numero in settings.par_numero]

    sortie = state.sortie_proposee(settings.state_db, etudiant, session, principale) or {}
    ligne = state.statut(settings.state_db, etudiant, session, principale) or {}
    verdict = str(ligne.get("verdict", ""))
    if sortie:
        reponse["extrait"] = {
            "statut": ligne.get("statut", state.STATUT_A_FAIRE),
            "verdict": verdict,
            "verdict_texte": VERDICTS.get(verdict.lower(), ""),
            "proposition": _substance(sortie),
            "inconnues": _chercher(sortie, "unknowns", "missing_information",
                                   "identified_unknowns", "informations_manquantes"),
            "questions": _chercher(sortie, "questions_for_human", "questions",
                                   "questions_for_student"),
            "signalements": _chercher(sortie, "verification_flags", "signalements", "flags"),
        }
        reponse["message"] = MESSAGES_QUESTION["rattachee_avec_contenu"].format(
            position=reponse["position"], libelle=etape.libelle)
    else:
        reponse["message"] = MESSAGES_QUESTION["rattachee_sans_contenu"].format(
            position=reponse["position"], libelle=etape.libelle)
    return reponse


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
        with urllib.request.urlopen(requete, timeout=(etape.timeout or settings.timeout)) as reponse:
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
            "telechargeable": bool(entree.get("file_name")),
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
