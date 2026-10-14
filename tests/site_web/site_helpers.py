"""Aides de test du SITE : aucun réseau, aucun agent, aucun modèle.

L'orchestrateur est remplacé par un double : le site ne doit parler QU'À lui, et les tests le
vérifient. Le double retient chaque appel reçu.
"""

import dataclasses
import pathlib
import re
import sys

import pytest
from fastapi.testclient import TestClient

RACINE = pathlib.Path(__file__).resolve().parents[2]
if str(RACINE / "src") not in sys.path:
    sys.path.insert(0, str(RACINE / "src"))

from site_web.core import securite  # noqa: E402
from site_web.core.config import charger  # noqa: E402
from site_web.storage import comptes  # noqa: E402

ETAPES = [(1, "Sujet"), (2, "Problème de recherche"), (3, "Revue de littérature"),
          (4, "Problématique"), (5, "Hypothèses")]

RESULTAT = {
    "resume": "Résumé proposé par l'agent. <script>alert('xss')</script>",
    "corpus": {"themes": [{"theme": "Productivité mesurée", "documents": 14,
                           "apport": "Effets positifs sur les tâches individuelles."}]},
    "unknowns": ["Aucune donnée sur les PME d'Abidjan."],
    "limits_of_this_output": ["Trois bases de données gratuites seulement."],
    "questions_for_human": ["Un secteur d'activité particulier ?"],
    "agent": "internal_metadata_should_never_be_shown",
}


class OrchestrateurSimule:
    """Double de l'orchestrateur : réponses fixes, appels retenus (aucun réseau)."""

    def __init__(self, en_panne=False):
        self.appels: list[tuple[str, str]] = []
        self.en_panne = en_panne
        # Code HTTP porté par l'erreur simulée : 500 (panne) par défaut, 404 pour une ressource
        # inconnue. Le site doit renvoyer CE code, jamais 200.
        self.statut_erreur = 500
        self.etape_ouverte = 3

    def _retenir(self, chemin, methode):
        self.appels.append((methode, chemin))
        if self.en_panne:
            from site_web.clients.orchestrateur import ErreurSite

            raise ErreurSite("La plateforme d'accompagnement ne répond pas pour le moment.",
                             statut=self.statut_erreur)

    def sante(self):
        return True

    def dossier(self, etudiant, session):
        self._retenir(f"/dossiers/{etudiant}/{session}", "GET")
        return {
            "etudiant": etudiant, "session": session, "sujet": "Mon sujet",
            "etape_ouverte": self.etape_ouverte, "libelle": "Revue de littérature",
            "statut": "proposee", "verdict": "verified", "quota_restant": 17, "quota_max": 20,
            "etapes": [{"numero": n, "libelle": lib} for n, lib in ETAPES],
            "avancement": [{"numero": n, "libelle": lib, "maj_le": "2026-10-11T09:00:00+00:00",
                            "verdict": "verified",
                            "statut": ("validee" if n < self.etape_ouverte
                                       else ("proposee" if n == self.etape_ouverte
                                             else "a_faire"))}
                           for n, lib in ETAPES],
        }

    def creer_dossier(self, etudiant, session, sujet, contexte):
        self._retenir(f"/dossiers/{etudiant}/{session}", "POST")
        return self.dossier(etudiant, session)

    def lancer_etape(self, etudiant, session):
        self._retenir(f"/dossiers/{etudiant}/{session}/etape", "POST")
        return {"etape": 3, "verdict": "verified", "quota_restant": 16}

    def decider(self, etudiant, session, decision, commentaire=""):
        self._retenir(f"/dossiers/{etudiant}/{session}/decision", "POST")
        return {"etape": 3, "statut": "validee", "etape_suivante": 4}

    def etape(self, etudiant, session, numero=None):
        self._retenir(f"/dossiers/{etudiant}/{session}/etape", "GET")
        return {"numero": 3, "libelle": "Revue de littérature", "statut": "proposee",
                "ouverte": True, "verdict": "verified",
                "verdict_texte": "Un contrôle indépendant a examiné cette proposition.",
                "resultat": RESULTAT, "inconnues": RESULTAT["unknowns"],
                "limites": RESULTAT["limits_of_this_output"],
                "questions": RESULTAT["questions_for_human"], "signalements": []}

    def documents(self, etudiant, session):
        self._retenir(f"/dossiers/{etudiant}/{session}/documents", "GET")
        return {"entries": [{"doc_id": "d1", "titre": "Un article", "auteurs": "Auteur, A.",
                             "annee": 2022, "revue": "Revue", "lien": "https://exemple.org",
                             "telechargeable": True}],
                "resume": {"references": 1, "telecharges": 1}}

    def fichier_document(self, etudiant, session, doc_id):
        self._retenir(f"/dossiers/{etudiant}/{session}/documents/{doc_id}/fichier", "GET")
        return b"%PDF-1.4 contenu"

    def bibliographie(self, etudiant, session, format):
        self._retenir(f"/dossiers/{etudiant}/{session}/bibliographie", "GET")
        return b"@article{cle, title = {Un article}}"

    def agents(self):
        self._retenir("/agents", "GET")
        return {"total": 2, "en_ligne": 1,
                "agents": [{"agent": "literature_review_agent", "libelle": "Revue de littérature",
                            "etape": 3, "en_ligne": True, "ecarts": []},
                           {"agent": "discussion_agent", "libelle": "Discussion", "etape": 11,
                            "en_ligne": False, "ecarts": []}]}

    def parcours(self):
        """La carte publique des étapes, telle que la page d'accueil l'affiche."""
        self._retenir("/parcours", "GET")
        return {"etapes": [{"numero": n, "position": rang + 1, "libelle": lib}
                           for rang, (n, lib) in enumerate(ETAPES)]}


@pytest.fixture
def site(tmp_path, monkeypatch):
    """Le site, isolé : base temporaire, clé de formulaire temporaire, orchestrateur simulé."""
    from site_web import main as main_site

    # Le cache de la page d'accueil est GLOBAL (il dure une minute) : on le vide pour que chaque
    # test parte d'un état propre, sinon un test hérite de la carte mémorisée par le précédent.
    main_site._CACHE_PARCOURS.update(quand=0.0, etapes=[])
    reglages = dataclasses.replace(charger(), base_comptes=tmp_path / "site.db")
    monkeypatch.setattr(main_site, "REGLAGES", reglages)
    monkeypatch.setattr(main_site, "_CLE_CSRF", tmp_path / ".site-csrf")
    simulé = OrchestrateurSimule()
    monkeypatch.setattr(main_site, "ORCHESTRATEUR", simulé)
    client = TestClient(main_site.app, follow_redirects=False)
    return client, simulé, reglages


def csrf_du(client) -> str:
    """Le jeton de formulaire tel qu'il est réellement servi dans la page."""
    page = client.get("/connexion")
    trouve = re.search(r'name="csrf" value="([^"]+)"', page.text)
    return trouve.group(1) if trouve else ""


def creer_compte(reglages, identifiant, mot_de_passe="motdepasse-solide", admin=False):
    comptes.creer_compte(reglages.base_comptes, identifiant, securite.hacher(mot_de_passe),
                         est_admin=admin)


def connecter(client, reglages, identifiant, admin=False, mot_de_passe="motdepasse-solide"):
    """Crée le compte si besoin et pose la session dans le client de test."""
    if comptes.identifiant_libre(reglages.base_comptes, identifiant):
        creer_compte(reglages, identifiant, mot_de_passe, admin)
    jeton = comptes.ouvrir_session(reglages.base_comptes, identifiant, 12)
    client.cookies.set("session", jeton)
    return jeton


def ouvrir_memoire(reglages, identifiant, session="mon-memoire", sujet="Mon sujet"):
    comptes.creer_memoire(reglages.base_comptes, identifiant, session, sujet)
    return session


def texte(page) -> str:
    """Le texte de la page, apostrophes normalisées : on teste le CONTENU, pas l'échappement
    (l'échappement lui-même est vérifié par le test de non-exécution du script)."""
    return page.text.replace("&#39;", "'").replace("\u2019", "'")
