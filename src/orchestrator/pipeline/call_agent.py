"""Appel d'un agent.

En usage réel : appel **HTTP local** (`127.0.0.1:port`) — les agents ne sont jamais exposés à
Internet, l'orchestrateur est leur unique client. En test : un `transport` injecté remplace l'appel
réseau, ce qui permet de valider tout l'enchaînement sans lancer un seul agent et sans aucun LLM.

Aucune clé, aucun secret ne traverse cette couche.
"""

import json
import urllib.error
import urllib.request

from ..core.errors import EtatErreur, OrchestratorError


def appeler(url: str, charge: dict, timeout: int, transport=None) -> dict:
    """Appelle un agent et renvoie sa réponse JSON.

    Les erreurs sont traduites en messages destinés à l'ÉTUDIANT : jamais une trace technique.
    """
    if transport is not None:
        return transport(url, charge)

    donnees = json.dumps(charge, ensure_ascii=False).encode("utf-8")
    requete = urllib.request.Request(
        url, data=donnees, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                     # Connexion fermée après la réponse : un agent qui rend une erreur
                     # sans corps (502 d'uvicorn) ne peut plus bloquer l'attente.
                     "Connection": "close"})
    try:
        with urllib.request.urlopen(requete, timeout=timeout) as reponse:
            corps = reponse.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode("utf-8", errors="replace")[:400]
        raise OrchestratorError(
            EtatErreur.AGENT_EN_ECHEC,
            "Cette étape n'a pas pu aboutir. Ton dossier est conservé : tu pourras la relancer.",
            f"HTTP {erreur.code} sur {url} : {detail}") from erreur
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        raise OrchestratorError(
            EtatErreur.AGENT_INDISPONIBLE,
            "Le service de cette étape ne répond pas pour le moment. Ton dossier est conservé.",
            f"{type(erreur).__name__} sur {url}") from erreur

    if not corps:
        return {}
    try:
        return json.loads(corps)
    except ValueError as erreur:
        raise OrchestratorError(
            EtatErreur.AGENT_EN_ECHEC,
            "Cette étape a renvoyé une réponse illisible : rien n'a été enregistré comme validé.",
            f"réponse non JSON sur {url}") from erreur
