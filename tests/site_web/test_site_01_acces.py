"""Accès, mots de passe, invitations, protection des formulaires, en-têtes.

Chaque test décrit un comportement de SÉCURITÉ attendu, pas un détail d'implémentation.
"""

from site_helpers import connecter, creer_compte, csrf_du, ouvrir_memoire

from site_web.storage import comptes


# --------------------------------------------------------------------- invitation
def test_une_invitation_valide_ouvre_la_creation_du_mot_de_passe(site):
    client, _, reglages = site
    comptes.creer_invitation(reglages.base_comptes, "jeton-invitation-1", "etudiant@exemple.edu")

    page = client.get("/invitation/jeton-invitation-1")

    assert page.status_code == 200
    assert "Choisissez votre mot de passe" in page.text
    assert "10 caractères minimum" in page.text


def test_une_invitation_inconnue_est_refusee_sans_rien_reveler(site):
    client, _, _ = site

    reponse = client.get("/invitation/jeton-qui-nexiste-pas")

    assert reponse.status_code == 303
    assert reponse.headers["location"].startswith("/connexion")


def test_une_invitation_ne_sert_qu_une_fois(site):
    client, _, reglages = site
    comptes.creer_invitation(reglages.base_comptes, "jeton-unique", "")
    jeton_csrf = csrf_du(client)

    premiere = client.post("/activer", data={
        "csrf": jeton_csrf, "jeton": "jeton-unique",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide"})

    assert premiere.status_code == 303
    assert premiere.headers["location"] == "/mes-memoires"
    assert "session" in premiere.headers.get("set-cookie", "")
    # La seconde tentative, avec le même jeton, est refusée.
    seconde = client.get("/invitation/jeton-unique")
    assert seconde.status_code == 303


def test_un_mot_de_passe_trop_court_est_refuse(site):
    client, _, reglages = site
    comptes.creer_invitation(reglages.base_comptes, "jeton-court", "")

    reponse = client.post("/activer", data={
        "csrf": csrf_du(client), "jeton": "jeton-court",
        "mot_de_passe": "court", "confirmation": "court"})

    assert reponse.status_code == 303
    assert "invitation/jeton-court" in reponse.headers["location"]
    assert comptes.nombre_comptes(reglages.base_comptes) == 0


def test_les_deux_mots_de_passe_doivent_correspondre(site):
    client, _, reglages = site
    comptes.creer_invitation(reglages.base_comptes, "jeton-diff", "")

    reponse = client.post("/activer", data={
        "csrf": csrf_du(client), "jeton": "jeton-diff",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-autre-mot-de-passe"})

    assert reponse.status_code == 303
    assert comptes.nombre_comptes(reglages.base_comptes) == 0


def test_le_mot_de_passe_n_est_jamais_stocke_en_clair(site):
    client, _, reglages = site
    comptes.creer_invitation(reglages.base_comptes, "jeton-clair", "")
    client.post("/activer", data={
        "csrf": csrf_du(client), "jeton": "jeton-clair",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide"})

    contenu = reglages.base_comptes.read_bytes()
    assert b"un-mot-de-passe-solide" not in contenu
    assert contenu.count(b"scrypt$") >= 1


# --------------------------------------------------------------------- connexion
def test_la_connexion_avec_un_bon_mot_de_passe_ouvre_une_session(site):
    client, _, reglages = site
    creer_compte(reglages, "etudiant-1", "mot-de-passe-correct")

    reponse = client.post("/connexion", data={
        "csrf": csrf_du(client), "identifiant": "etudiant-1",
        "mot_de_passe": "mot-de-passe-correct"})

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/mes-memoires"
    cookie = reponse.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_le_message_est_identique_que_le_compte_existe_ou_non(site):
    client, _, reglages = site
    creer_compte(reglages, "etudiant-1", "mot-de-passe-correct")
    jeton = csrf_du(client)

    compte_inconnu = client.post("/connexion", data={
        "csrf": jeton, "identifiant": "personne", "mot_de_passe": "mot-de-passe-correct"})
    mauvais_mot_de_passe = client.post("/connexion", data={
        "csrf": jeton, "identifiant": "etudiant-1", "mot_de_passe": "faux"})

    assert compte_inconnu.headers["location"] == mauvais_mot_de_passe.headers["location"]


def test_la_connexion_est_bloquee_apres_cinq_echecs(site):
    client, _, reglages = site
    creer_compte(reglages, "etudiant-1", "mot-de-passe-correct")
    jeton = csrf_du(client)
    for _ in range(5):
        client.post("/connexion", data={"csrf": jeton, "identifiant": "etudiant-1",
                                        "mot_de_passe": "faux"})

    # Même avec le BON mot de passe, l'accès reste bloqué.
    reponse = client.post("/connexion", data={"csrf": jeton, "identifiant": "etudiant-1",
                                              "mot_de_passe": "mot-de-passe-correct"})

    assert reponse.status_code == 303
    assert "bloqu" in reponse.headers["location"]


def test_un_formulaire_sans_jeton_est_refuse(site):
    client, _, reglages = site
    creer_compte(reglages, "etudiant-1", "mot-de-passe-correct")

    reponse = client.post("/connexion", data={
        "csrf": "faux-jeton", "identifiant": "etudiant-1", "mot_de_passe": "mot-de-passe-correct"})

    assert reponse.status_code == 303
    assert reponse.headers["location"].startswith("/connexion")
    assert "session" not in reponse.headers.get("set-cookie", "")


def test_la_deconnexion_detruit_la_session(site):
    client, _, reglages = site
    connecter(client, reglages, "etudiant-1")

    reponse = client.get("/deconnexion")

    assert reponse.status_code == 303
    assert client.get("/mes-memoires").status_code == 303


# -------------------------------------------------------------------- inscription
def test_l_inscription_par_email_cree_le_compte_et_ouvre_une_session(site):
    """Aucune invitation : l'adresse e-mail suffit à créer son accès."""
    client, _, reglages = site

    reponse = client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "etudiante@exemple.com",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide"})

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/mes-memoires"
    assert "session" in reponse.headers.get("set-cookie", "")
    assert comptes.compte(reglages.base_comptes, "etudiante@exemple.com") is not None


def test_l_email_est_l_identifiant_de_connexion(site):
    client, _, reglages = site
    client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "Etudiante@Exemple.com",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide"})
    client.cookies.clear()

    # L'adresse est normalisée en minuscules, et c'est elle qui sert à se connecter.
    reponse = client.post("/connexion", data={
        "csrf": csrf_du(client), "identifiant": "etudiante@exemple.com",
        "mot_de_passe": "un-mot-de-passe-solide"})

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/mes-memoires"


def test_l_inscription_refuse_une_adresse_invalide(site):
    client, _, reglages = site

    reponse = client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "pas-une-adresse",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide"})

    assert reponse.status_code == 303
    assert reponse.headers["location"].startswith("/inscription")
    assert comptes.nombre_comptes(reglages.base_comptes) == 0


def test_l_inscription_refuse_une_adresse_deja_prise(site):
    """On ne peut pas prendre la place d'un compte existant — et surtout pas ouvrir sa session."""
    client, _, reglages = site
    creer_compte(reglages, "etudiante@exemple.com")

    reponse = client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "etudiante@exemple.com",
        "mot_de_passe": "un-mot-de-passe-solide", "confirmation": "un-mot-de-passe-solide"})

    assert reponse.status_code == 303
    assert "existe" in reponse.headers["location"]
    assert "session" not in reponse.headers.get("set-cookie", "")
    assert comptes.nombre_comptes(reglages.base_comptes) == 1


def test_l_inscription_exige_un_mot_de_passe_solide(site):
    client, _, reglages = site

    reponse = client.post("/inscription", data={
        "csrf": csrf_du(client), "email": "etudiante@exemple.com",
        "mot_de_passe": "court", "confirmation": "court"})

    assert reponse.status_code == 303
    assert comptes.nombre_comptes(reglages.base_comptes) == 0


def test_un_mot_de_passe_seul_ne_suffit_pas_pour_ouvrir_le_dossier_d_un_autre(site):
    """Le mot de passe n'est pas une formalité : sans lui, n'importe qui lirait ce mémoire."""
    client, _, reglages = site
    creer_compte(reglages, "etudiante@exemple.com", "son-vrai-mot-de-passe")
    ouvrir_memoire(reglages, "etudiante@exemple.com", "son-memoire")

    mauvais = client.post("/connexion", data={
        "csrf": csrf_du(client), "identifiant": "etudiante@exemple.com",
        "mot_de_passe": "devine"})
    assert mauvais.status_code == 303
    assert client.get("/memoire/son-memoire").status_code == 303

    bon = client.post("/connexion", data={
        "csrf": csrf_du(client), "identifiant": "etudiante@exemple.com",
        "mot_de_passe": "son-vrai-mot-de-passe"})
    assert bon.status_code == 303
    assert client.get("/memoire/son-memoire").status_code == 200


# ---------------------------------------------------------------- en-têtes servis
def test_les_en_tetes_de_protection_sont_servis(site):
    client, _, _ = site

    entetes = client.get("/connexion").headers

    politique = entetes["content-security-policy"]
    # Les scripts viennent UNIQUEMENT de nos propres fichiers : ni tiers, ni code en ligne,
    # ni eval. C'est ce qui permet du dynamisme sans ouvrir la porte à du code étranger.
    assert "script-src 'self'" in politique
    assert "script-src 'none'" not in politique
    assert "'unsafe-inline'" not in politique.split("script-src")[1].split(";")[0]
    assert "'unsafe-eval'" not in politique
    assert "frame-ancestors 'none'" in politique
    assert "base-uri 'none'" in politique
    assert entetes["x-frame-options"] == "DENY"
    assert entetes["x-content-type-options"] == "nosniff"
    assert entetes["referrer-policy"] == "same-origin"
    assert "max-age=31536000" in entetes["strict-transport-security"]


def test_une_page_privee_sans_session_renvoie_a_la_connexion(site):
    client, _, _ = site

    reponse = client.get("/mes-memoires")

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/connexion"


def test_le_dossier_de_quelqu_un_d_autre_est_inaccessible(site):
    """Isolation : l'identifiant du mémoire ne suffit pas, il faut qu'il soit le sien."""
    client, _, reglages = site
    creer_compte(reglages, "etudiant-1")
    creer_compte(reglages, "etudiant-2")
    ouvrir_memoire(reglages, "etudiant-2", "memoire-de-deux")
    connecter(client, reglages, "etudiant-1")

    for chemin in ("/memoire/memoire-de-deux", "/memoire/memoire-de-deux/etape",
                   "/memoire/memoire-de-deux/documents", "/memoire/memoire-de-deux/journal"):
        reponse = client.get(chemin)
        assert reponse.status_code == 303, chemin
        assert reponse.headers["location"] == "/mes-memoires", chemin


def test_le_tableau_de_bord_est_interdit_a_un_etudiant(site):
    client, _, reglages = site
    connecter(client, reglages, "etudiant-1", admin=False)

    reponse = client.get("/tableau-de-bord")

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/mes-memoires"


def test_le_tableau_de_bord_est_ouvert_a_un_administrateur(site):
    client, _, reglages = site
    connecter(client, reglages, "responsable", admin=True)

    page = client.get("/tableau-de-bord")

    assert page.status_code == 200
    assert "Tableau de bord" in page.text
    assert "Créer une invitation" in page.text
