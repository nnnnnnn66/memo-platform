"""L'ORCHESTRATEUR RÉPOND : il désigne l'étape, appelle SON agent, et rapporte la réponse.

Demande du porteur :

    « quand je clique sur Sujet, l'agent Sujet doit être présent et répondre à toutes mes requêtes ;
     si je pose une question qui ne relève pas de ses compétences, alors l'orchestrateur intervient
     et appelle directement l'agent concerné, et la réponse doit être là. »

Le partage des rôles est celui de toujours :

- **l'orchestrateur est le seul à connaître la carte.** Il désigne l'étape compétente
  (`core/routage.py`, vocabulaire fermé, DÉTERMINISTE — aucun modèle, coût 0, choix explicable) ;
- **l'agent répond**, dans son périmètre, avec le contexte du dossier réel ;
- **l'orchestrateur relaie.** Si l'agent interrogé déclare que la question relève d'une AUTRE étape,
  l'orchestrateur appelle cet agent-là — une fois, jamais en boucle — au lieu de renvoyer à
  l'étudiant un « ce n'est pas mon domaine ».

Deux garde-fous, appris à la dure :

1. **Aucun agent n'est modifié par un autre** : l'orchestrateur ne parle aux agents que par leur
   route déclarée (`route_question` dans `settings-orchestrateur.yaml`). Un agent qui n'en déclare
   pas n'est pas deviné : l'orchestrateur le DIT.
2. **Une réponse ne consomme pas une analyse** : `interroger` n'écrit rien dans le dossier, ne
   touche pas au quota et ne lance aucune campagne. Répondre est gratuit en quota ; c'est le prix
   à payer pour que l'étudiant ose poser ses questions.
"""

from __future__ import annotations

import json

from ..storage import state
from . import call_agent
from ..core import routage as routage_module
from ..core.errors import EtatErreur, OrchestratorError

# Bornes du contexte transmis à l'agent : assez pour qu'il raisonne sur le dossier réel, pas assez
# pour qu'il déborde (et jamais un digest tronqué EN SILENCE — la coupe est marquée).
_MAX_CONTEXTE = 12_000
_MAX_PAR_ETAPE = 6_000


def _tronque(texte: str, limite: int) -> str:
    if len(texte) <= limite:
        return texte
    return texte[:limite] + f"\n[… coupé : {len(texte) - limite} caractères de plus dans le dossier]"


def _etape_de(settings, numero: int):
    return settings.par_numero.get(numero)


def _contexte(settings, etudiant: str, session: str, numero: int) -> str:
    """Le dossier RÉEL de l'étudiant : la production de l'étape désignée et celles de ses amont.

    Un digest tronqué sans le dire a déjà fait produire de faux constats sur cette plateforme : ici
    l'étape interrogée reçoit SA production en premier, puis les amont VALIDÉES, et toute coupe est
    écrite noir sur blanc.
    """
    blocs: list[str] = []
    etape = _etape_de(settings, numero)
    a_voir = [numero] + list((etape.upstream or {}).values() if etape else [])
    for rang, n in enumerate(a_voir):
        sortie = state.sortie_validee(settings.state_db, etudiant, session, n)
        if not sortie:
            continue
        cible = _etape_de(settings, n)
        titre = f"{cible.libelle} (étape {n})" if cible else f"étape {n}"
        contenu = _tronque(json.dumps(sortie, ensure_ascii=False, indent=1), _MAX_PAR_ETAPE)
        blocs.append(f"--- {titre} ---\n{contenu}")
    if not blocs:
        return ""
    return _tronque("\n\n".join(blocs), _MAX_CONTEXTE)


def _appeler(settings, etudiant: str, session: str, numero: int, question: str,
             transport=None) -> dict:
    """Appelle l'agent de l'étape `numero` sur sa route d'interrogation."""
    etape = _etape_de(settings, numero)
    if etape is None:
        raise OrchestratorError(EtatErreur.ETAPE_INCONNUE,
                                "Cette étape ne fait pas partie de ton parcours.")
    if not etape.route_question:
        raise OrchestratorError(
            EtatErreur.AGENT_INDISPONIBLE,
            f"L'agent de l'étape « {etape.libelle} » ne sait pas encore répondre à une question "
            "directe : sa production reste consultable, et il répondra dès sa prochaine mise à jour.")
    charge = {
        "student_id": etudiant,
        "session_id": session,
        "question": question,
        "contexte": _contexte(settings, etudiant, session, numero),
    }
    return call_agent.appeler(etape.url_question(settings.hote), charge,
                              settings.timeout, transport=transport)


def interroger(settings, etudiant: str, session: str, question: str, transport=None) -> dict:
    """Désigne l'étape, fait répondre son agent, et relaie si la question appartient à une autre.

    Ne lève que sur une entrée invalide ou un dossier inconnu. Un échec d'agent est DÉCLARÉ dans la
    réponse (`repondu: false`) : l'étudiant doit voir un message honnête, jamais un silence.
    """
    question = (question or "").strip()
    if len(question) < 3:
        raise OrchestratorError(EtatErreur.ENTREE_INVALIDE, "Écris une question un peu plus longue.")
    if len(question) > 4000:
        raise OrchestratorError(EtatErreur.ENTREE_INVALIDE, "Question trop longue (4000 caractères maximum).")
    if state.dossier(settings.state_db, etudiant, session) is None:
        raise OrchestratorError(EtatErreur.DOSSIER_INCONNU, "Ce travail est introuvable.")

    routage = routage_module.router(question)
    numero = routage.get("principale")
    if numero is None:
        # Rien de reconnu : on le DIT. Deviner ferait répondre un agent hors de son domaine, et
        # l'étudiant croirait son point traité.
        return {
            "repondu": False,
            "raison": "question_non_rattachee",
            "question": question,
            "etape": None, "agent": None, "libelle": None,
            "message": "Je n'ai pas su rattacher ta question à une étape précise. Dis-moi sur quoi "
                       "elle porte (ton sujet, ta méthode, tes résultats…) et je te réponds.",
            "routage": routage,
        }

    etape = _etape_de(settings, numero)
    try:
        reponse = _appeler(settings, etudiant, session, numero, question, transport=transport)
    except OrchestratorError as exc:
        return {"repondu": False, "raison": exc.etat.value, "question": question,
                "etape": numero, "agent": etape.agent if etape else None,
                "libelle": etape.libelle if etape else None,
                "message": exc.detail, "routage": routage}

    relaye_depuis = None
    # L'agent a reconnu que la question n'était pas la sienne : on appelle LE BON agent, une fois.
    if reponse.get("dans_perimetre") is False and reponse.get("etape_competente"):
        vise = int(reponse["etape_competente"])
        cible = _etape_de(settings, vise)
        if vise != numero and cible is not None and cible.route_question:
            try:
                seconde = _appeler(settings, etudiant, session, vise, question, transport=transport)
            except OrchestratorError:
                seconde = None
            if seconde and (seconde.get("reponse") or "").strip():
                relaye_depuis = {"etape": numero, "libelle": etape.libelle if etape else ""}
                reponse, numero, etape = seconde, vise, cible

    return {
        "repondu": bool((reponse.get("reponse") or "").strip()),
        "question": question,
        "etape": numero,
                "agent": getattr(etape, "agent", None),
        "libelle": getattr(etape, "libelle", None),
        "reponse": reponse.get("reponse", ""),
        "dans_perimetre": reponse.get("dans_perimetre"),
        "etape_competente": reponse.get("etape_competente"),
        "relaye_depuis": relaye_depuis,
        "annotations_injection": reponse.get("annotations", []),
        "routage": routage,
    }
