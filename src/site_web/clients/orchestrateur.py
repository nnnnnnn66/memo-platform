"""SEUL point de contact du site avec le monde extérieur : l'orchestrateur.

Le site ne connaît PAS les agents, leurs adresses, ni leurs API. Il ignore aussi où sont stockés
les dossiers. Tout passe par l'orchestrateur, en local. C'est ce qui permet de remplacer ou
d'ajouter un agent sans jamais toucher au site.

Les erreurs sont traduites en messages destinés à l'ÉTUDIANT : jamais une trace technique.
"""

import json
import urllib.error
import urllib.parse
import urllib.request


class ErreurSite(Exception):
    """Erreur affichable telle quelle à l'étudiant.

    `statut` est le code HTTP que le SITE renverra : une ressource inconnue (404) n'est pas une
    panne (500). Sans cela, le site répondait 200 pour une page d'erreur — un client, un moteur de
    recherche ou un moniteur ne pouvaient pas savoir qu'il y avait eu une erreur.
    """

    def __init__(self, message: str, technique: str = "", statut: int = 500):
        super().__init__(message)
        self.message = message
        self.technique = technique or message
        self.statut = statut


class Orchestrateur:
    def __init__(self, url: str, timeout: int = 1800):
        self.url = url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ interne
    def _appeler(self, chemin: str, methode: str = "GET", corps: dict | None = None,
                 brut: bool = False, timeout: int | None = None):
        adresse = f"{self.url}{chemin}"
        donnees = json.dumps(corps, ensure_ascii=False).encode("utf-8") if corps else None
        requete = urllib.request.Request(
            adresse, data=donnees, method=methode,
            headers={"Accept": "application/json", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(requete, timeout=timeout or self.timeout) as reponse:
                contenu = reponse.read()
                return contenu if brut else (json.loads(contenu.decode("utf-8")) if contenu else {})
        except urllib.error.HTTPError as erreur:
            detail = erreur.read().decode("utf-8", errors="replace")
            raise self._traduire(erreur.code, detail, adresse) from erreur
        except (urllib.error.URLError, TimeoutError, OSError) as erreur:
            raise ErreurSite(
                "La plateforme d'accompagnement ne répond pas pour le moment. "
                "Votre travail est conservé : réessayez dans quelques instants.",
                f"{type(erreur).__name__} sur {adresse}") from erreur

    @staticmethod
    def _traduire(code: int, detail: str, adresse: str) -> ErreurSite:
        """Un code d'erreur devient une phrase que l'étudiant comprend.

        Le code HTTP est CONSERVÉ dans l'`ErreurSite` : `404` reste « ressource inconnue », les
        autres codes remontent tels quels. Le site renverra donc ce code, jamais 200.
        """
        message = None
        try:
            charge = json.loads(detail)
            message = (charge.get("detail") or {}).get("message") if isinstance(
                charge.get("detail"), dict) else None
        except (ValueError, AttributeError):
            pass
        if message:
            return ErreurSite(message, f"HTTP {code} sur {adresse} : {detail[:300]}", statut=code)
        if code == 404:
            return ErreurSite("Ce dossier est introuvable.", f"HTTP 404 sur {adresse}", statut=404)
        if code == 429:
            return ErreurSite(
                "Vous avez atteint votre nombre d'analyses du jour. "
                "Votre dossier est conservé : vous pourrez reprendre demain.",
                f"HTTP 429 sur {adresse}", statut=429)
        if code == 409:
            return ErreurSite(
                "Cette étape attend votre décision : validez-la ou demandez une révision.",
                f"HTTP 409 sur {adresse}", statut=409)
        return ErreurSite(
            "Cette action n'a pas pu aboutir. Rien n'a été validé ; vous pouvez réessayer.",
            f"HTTP {code} sur {adresse} : {detail[:300]}", statut=code)

    # ------------------------------------------------------------------- lecture
    def sante(self) -> bool:
        try:
            self._appeler("/health")
            return True
        except ErreurSite:
            return False

    def dossier(self, etudiant: str, session: str) -> dict:
        return self._appeler(f"/dossiers/{self._c(etudiant)}/{self._c(session)}")

    def agents(self) -> dict:
        return self._appeler("/agents")

    def parcours(self) -> dict:
        """La carte des étapes — appelée par la page d'accueil, donc avec un délai COURT : un
        visiteur ne doit jamais attendre qu'un service éteint veuille bien répondre."""
        return self._appeler("/parcours", timeout=4)

    def etape(self, etudiant: str, session: str, numero: int | None = None) -> dict:
        """L'étape à afficher : sa proposition, ce qui reste inconnu, ses limites, ses questions."""
        adresse = f"/dossiers/{self._c(etudiant)}/{self._c(session)}/etape"
        if numero:
            adresse += f"?n={int(numero)}"
        return self._appeler(adresse)

    # ------------------------------------------------------------------ écriture
    def creer_dossier(self, etudiant: str, session: str, sujet: str,
                      contexte: dict | str) -> dict:
        return self._appeler(f"/dossiers/{self._c(etudiant)}/{self._c(session)}", "POST",
                             {"sujet": sujet, "sujet_contexte": contexte})

    def lancer_etape(self, etudiant: str, session: str) -> dict:
        return self._appeler(f"/dossiers/{self._c(etudiant)}/{self._c(session)}/etape", "POST", {})

    def decider(self, etudiant: str, session: str, decision: str, commentaire: str = "") -> dict:
        return self._appeler(f"/dossiers/{self._c(etudiant)}/{self._c(session)}/decision", "POST",
                             {"decision": decision, "commentaire": commentaire})

    # -------------------------------------------------------- documents & export
    def documents(self, etudiant: str, session: str) -> dict:
        return self._appeler(
            f"/dossiers/{self._c(etudiant)}/{self._c(session)}/documents")

    def fichier_document(self, etudiant: str, session: str, doc_id: str) -> bytes:
        return self._appeler(
            f"/dossiers/{self._c(etudiant)}/{self._c(session)}/documents/"
            f"{self._c(doc_id)}/fichier", brut=True)

    def bibliographie(self, etudiant: str, session: str, format: str) -> tuple:
        adresse = (f"/dossiers/{self._c(etudiant)}/{self._c(session)}/bibliographie"
                   f"?format={urllib.parse.quote(format)}")
        contenu = self._appeler(adresse, brut=True)
        return contenu

    @staticmethod
    def _c(valeur: str) -> str:
        """Composant d'URL : encodé, jamais concaténé brut (anti-injection de chemin)."""
        return urllib.parse.quote(str(valeur), safe="")
