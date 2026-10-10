"""Le mot de passe arrive par courrier : c'est ce qui prouve que l'adresse est bien la sienne.

Aucun envoi réel dans ces tests : l'expédition est remplacée, et l'on vérifie ce qui PART et ce
qui est STOCKÉ. L'envoi réel est éprouvé séparément, avec un vrai compte.
"""

import re

import pytest

from site_helpers import csrf_du, ouvrir_memoire
from site_web.core import courriel, securite
from site_web.storage import comptes

MOTIF_MOT_DE_PASSE = re.compile(r"^\s{4}([a-z2-9]{4}-[a-z2-9]{4}-[a-z2-9]{4})\s*$", re.M)


@pytest.fixture
def smtp(monkeypatch):
    """Un compte d'envoi configuré, et l'expédition capturée au lieu d'être envoyée."""
    monkeypatch.setenv("MEMO_SMTP_HOST", "smtp.exemple.com")
    monkeypatch.setenv("MEMO_SMTP_PORT", "587")
    monkeypatch.setenv("MEMO_SMTP_USER", "plateforme@exemple.com")
    monkeypatch.setenv("MEMO_SMTP_PASSWORD", "mot-de-passe-smtp")
    monkeypatch.setenv("MEMO_SMTP_FROM", "plateforme@exemple.com")
    envois = []

    def capturer(destinataire, sujet, texte, transport=None):
        envois.append({"a": destinataire, "sujet": sujet, "texte": texte})

    monkeypatch.setattr(courriel, "envoyer", capturer)
    return envois


@pytest.fixture
def sans_smtp(monkeypatch):
    """Aucun compte d'envoi : le site doit rester utilisable."""
    for variable in ("MEMO_SMTP_HOST", "MEMO_SMTP_PORT", "MEMO_SMTP_USER",
                     "MEMO_SMTP_PASSWORD", "MEMO_SMTP_FROM"):
        monkeypatch.delenv(variable, raising=False)
    return None


# ------------------------------------------------------------- mot de passe par courrier
def test_l_adresse_seule_suffit_et_le_mot_de_passe_part_par_courrier(site, smtp):
    client, _, reglages = site

    reponse = client.post("/inscription", data={"csrf": csrf_du(client),
                                                "email": "etudiante@exemple.com"})

    assert reponse.status_code == 303
    assert reponse.headers["location"].startswith("/connexion")
    assert len(smtp) == 1
    assert smtp[0]["a"] == "etudiante@exemple.com"
    assert "mot de passe" in smtp[0]["sujet"].lower()
    assert comptes.compte(reglages.base_comptes, "etudiante@exemple.com") is not None


def test_le_mot_de_passe_recu_par_courrier_permet_d_entrer(site, smtp):
    client, _, _ = site
    client.post("/inscription", data={"csrf": csrf_du(client), "email": "etudiante@exemple.com"})
    trouve = MOTIF_MOT_DE_PASSE.search(smtp[0]["texte"])
    assert trouve, "le courrier doit contenir le mot de passe, lisiblement"
    mot_de_passe = trouve.group(1)
    client.cookies.clear()

    reponse = client.post("/connexion", data={"csrf": csrf_du(client),
                                              "identifiant": "etudiante@exemple.com",
                                              "mot_de_passe": mot_de_passe})

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/mes-memoires"


def test_le_mot_de_passe_envoye_n_est_pas_stocke_en_clair(site, smtp):
    client, _, reglages = site
    client.post("/inscription", data={"csrf": csrf_du(client), "email": "etudiante@exemple.com"})
    mot_de_passe = MOTIF_MOT_DE_PASSE.search(smtp[0]["texte"]).group(1)

    contenu = reglages.base_comptes.read_bytes()

    assert mot_de_passe.encode() not in contenu
    assert b"scrypt$" in contenu


def test_le_courrier_contient_le_lien_pour_entrer(site, smtp):
    client, _, _ = site
    client.post("/inscription", data={"csrf": csrf_du(client), "email": "etudiante@exemple.com"})

    assert "/connexion" in smtp[0]["texte"]


def test_la_meme_reponse_que_l_adresse_existe_deja(site, smtp):
    """On ne peut pas découvrir quelles adresses sont inscrites : réponse identique."""
    client, _, _ = site
    premiere = client.post("/inscription", data={"csrf": csrf_du(client),
                                                 "email": "etudiante@exemple.com"})
    seconde = client.post("/inscription", data={"csrf": csrf_du(client),
                                                "email": "etudiante@exemple.com"})

    assert premiere.headers["location"] == seconde.headers["location"]
    assert len(smtp) == 1  # aucun second courrier, et rien ne le laisse deviner


def test_une_adresse_invalide_n_envoie_rien(site, smtp):
    client, _, reglages = site
    reponse = client.post("/inscription", data={"csrf": csrf_du(client), "email": "pas-une-adresse"})

    assert reponse.status_code == 303
    assert smtp == []
    assert comptes.nombre_comptes(reglages.base_comptes) == 0


def test_une_panne_d_envoi_est_annoncee_a_l_etudiant(site, monkeypatch, smtp):
    client, _, _ = site

    def en_panne(destinataire, sujet, texte, transport=None):
        raise courriel.ErreurCourriel("Le courrier n'a pas pu être envoyé.")

    monkeypatch.setattr(courriel, "envoyer", en_panne)
    reponse = client.post("/inscription", data={"csrf": csrf_du(client),
                                                "email": "etudiante@exemple.com"})

    assert reponse.status_code == 303
    assert "inscription" in reponse.headers["location"]
    assert "courrier" in reponse.headers["location"]


# ------------------------------------------------------------------- sans compte d'envoi
def test_sans_compte_d_envoi_l_etudiant_choisit_son_mot_de_passe(site, sans_smtp):
    client, _, reglages = site
    reponse = client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "etudiante@exemple.com",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide"})

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/mes-memoires"
    assert comptes.compte(reglages.base_comptes, "etudiante@exemple.com") is not None


def test_sans_compte_d_envoi_la_page_ne_reclame_pas_de_mot_de_passe(site, smtp):
    """Le formulaire s'adapte : il ne demande un mot de passe que si personne ne peut l'envoyer."""
    client, _, _ = site
    avec = client.get("/inscription").text

    assert "Choisissez un mot de passe" not in avec
    assert "Recevoir mon mot de passe" in avec


# ------------------------------------------------------------------------ générateur
def test_le_mot_de_passe_fabrique_est_solide_et_lisible():
    mot_de_passe = securite.mot_de_passe_aleatoire()

    assert len(mot_de_passe) == 14
    assert mot_de_passe.count("-") == 2
    # Aucun caractère ambigu : il est recopié depuis un courrier.
    assert not set(mot_de_passe) & set("0O1lI")
    assert securite.mot_de_passe_valide(mot_de_passe)[0]
    assert securite.mot_de_passe_aleatoire() != mot_de_passe
