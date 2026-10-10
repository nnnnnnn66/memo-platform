"""Le mot de passe de l'étudiant, et le module de courrier.

Décision du porteur de projet : **l'étudiant choisit lui-même son mot de passe, et le confirme.**
C'est ce mot de passe qui protège son travail. Le module de courrier existe pour la seule chose
que le site ne sait pas encore faire — « mot de passe oublié » — et n'est donc pas branché sur
l'inscription : ces tests vérifient qu'il est prêt, et qu'il ne parle jamais en langage technique.
"""

import re

import pytest

from site_helpers import csrf_du
from site_web.core import courriel, securite
from site_web.storage import comptes


# ------------------------------------------------- inscription : mot de passe choisi
def test_l_inscription_exige_un_mot_de_passe_et_sa_confirmation(site):
    client, _, reglages = site

    reponse = client.post("/inscription", data={"csrf": csrf_du(client),
                                                "email": "etudiante@exemple.com"})

    assert reponse.status_code == 303
    assert reponse.headers["location"].startswith("/inscription")
    assert comptes.nombre_comptes(reglages.base_comptes) == 0


def test_une_confirmation_differente_est_refusee(site):
    """La confirmation existe pour éviter la faute de frappe qui enfermerait l'étudiant dehors."""
    client, _, reglages = site

    reponse = client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "etudiante@exemple.com",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide-2"})

    assert reponse.status_code == 303
    assert "identiques" in reponse.headers["location"]
    assert comptes.nombre_comptes(reglages.base_comptes) == 0


def test_le_mot_de_passe_choisi_permet_de_se_connecter(site):
    client, _, _ = site
    client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "etudiante@exemple.com",
        "mot_de_passe": "le-mot-de-passe-de-nadia", "confirmation": "le-mot-de-passe-de-nadia"})
    client.cookies.clear()

    reponse = client.post("/connexion", data={
        "csrf": csrf_du(client), "identifiant": "etudiante@exemple.com",
        "mot_de_passe": "le-mot-de-passe-de-nadia"})

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/mes-memoires"


def test_le_mot_de_passe_n_est_pas_stocke_en_clair(site):
    client, _, reglages = site
    client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "etudiante@exemple.com",
        "mot_de_passe": "le-mot-de-passe-de-nadia", "confirmation": "le-mot-de-passe-de-nadia"})

    contenu = reglages.base_comptes.read_bytes()

    assert b"le-mot-de-passe-de-nadia" not in contenu
    assert b"scrypt$" in contenu


def test_la_page_d_inscription_demande_le_mot_de_passe_et_sa_confirmation(site):
    client, _, _ = site

    page = client.get("/inscription").text

    assert "Choisissez votre mot de passe" in page
    assert "Confirmez votre mot de passe" in page


def test_l_adresse_deja_inscrite_est_refusee(site):
    client, _, reglages = site
    donnees = {"csrf": csrf_du(client), "email": "etudiante@exemple.com",
               "mot_de_passe": "le-mot-de-passe-de-nadia",
               "confirmation": "le-mot-de-passe-de-nadia"}
    client.post("/inscription", data=donnees)
    client.cookies.clear()

    reponse = client.post("/inscription", data=donnees)

    assert reponse.status_code == 303
    assert "existe" in reponse.headers["location"]
    assert "session" not in reponse.headers.get("set-cookie", "")
    assert comptes.nombre_comptes(reglages.base_comptes) == 1


# ------------------------------------------- le mot de passe fabriqué (module prêt)
def test_le_mot_de_passe_fabrique_est_solide_et_lisible():
    mot_de_passe = securite.mot_de_passe_aleatoire()

    assert len(mot_de_passe) == 14
    assert mot_de_passe.count("-") == 2
    # Aucun caractère ambigu : il serait recopié depuis un courrier.
    assert not set(mot_de_passe) & set("0O1lI")
    assert securite.mot_de_passe_valide(mot_de_passe)[0]
    assert securite.mot_de_passe_aleatoire() != mot_de_passe


def test_un_mot_de_passe_fabrique_est_reconnu_par_la_verification():
    """Le jour où « mot de passe oublié » sera branché, ce chemin doit déjà être juste."""
    mot_de_passe = securite.mot_de_passe_aleatoire()

    assert securite.verifier(mot_de_passe, securite.hacher(mot_de_passe))
    assert not securite.verifier(mot_de_passe + "x", securite.hacher(mot_de_passe))


# ---------------------------------------------------------------- module de courrier
def test_le_module_d_envoi_signale_clairement_qu_il_n_est_pas_configure(monkeypatch):
    monkeypatch.delenv("MEMO_SMTP_HOST", raising=False)

    assert courriel.est_configure() is False
    with pytest.raises(courriel.ErreurCourriel) as erreur:
        courriel.envoyer("etudiante@exemple.com", "Sujet", "Corps")
    assert "configuré" in str(erreur.value)


def test_le_module_d_envoi_lit_les_reglages_de_l_environnement(monkeypatch):
    monkeypatch.setenv("MEMO_SMTP_HOST", "smtp.exemple.com")
    monkeypatch.setenv("MEMO_SMTP_PORT", "587")
    monkeypatch.setenv("MEMO_SMTP_USER", "plateforme@exemple.com")
    monkeypatch.setenv("MEMO_SMTP_PASSWORD", "secret")
    monkeypatch.delenv("MEMO_SMTP_FROM", raising=False)

    assert courriel.est_configure() is True
    recus = []
    courriel.envoyer("etudiante@exemple.com", "Sujet", "Corps",
                     transport=lambda message: recus.append(message))

    assert len(recus) == 1
    assert recus[0]["To"] == "etudiante@exemple.com"
    # Sans expéditeur distinct, c'est le compte qui envoie.
    assert "plateforme@exemple.com" in recus[0]["From"]


def test_le_courrier_d_acces_porte_le_mot_de_passe_et_le_lien_d_entree():
    sujet, texte = courriel.courrier_acces("etudiante@exemple.com", "kfqm-2xta-9prz",
                                           "https://exemple.org")

    assert "mot de passe" in sujet.lower()
    assert "kfqm-2xta-9prz" in texte
    assert "https://exemple.org/connexion" in texte
    assert "etudiante@exemple.com" in texte
    assert re.search(r"^\s{4}kfqm-2xta-9prz\s*$", texte, re.M), "le mot de passe doit être isolé"


def test_une_panne_d_envoi_devient_un_message_pour_l_etudiant(monkeypatch):
    monkeypatch.setenv("MEMO_SMTP_HOST", "smtp.inexistant.exemple")
    monkeypatch.setenv("MEMO_SMTP_PORT", "1")
    monkeypatch.delenv("MEMO_SMTP_USER", raising=False)

    with pytest.raises(courriel.ErreurCourriel) as erreur:
        courriel.envoyer("etudiante@exemple.com", "Sujet", "Corps")

    assert "réessayez" in str(erreur.value).lower()
    assert "smtp" not in str(erreur.value).lower(), "aucun détail technique à l'écran"
