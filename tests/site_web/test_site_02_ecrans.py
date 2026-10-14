"""Les écrans : ce que l'étudiant voit, ce qu'il ne voit jamais, et les cas d'erreur.

On vérifie ici la PROMESSE du site : afficher sans réécrire, ne jamais exposer de donnée
interne, ne jamais exécuter ce que produit un agent, et dire clairement quand ça va mal.
"""

import pathlib

from site_helpers import connecter, csrf_du, ouvrir_memoire, texte


def _preparer(site, identifiant="etudiant-1", session="mon-memoire", admin=False):
    client, simule, reglages = site
    connecter(client, reglages, identifiant, admin=admin)
    ouvrir_memoire(reglages, identifiant, session)
    return client, simule, reglages


# ------------------------------------------------------------------- parcours
def test_le_parcours_affiche_l_action_a_faire_et_l_avancement(site):
    """Le tableau de bord montre CE QU'IL Y A À FAIRE, pas un second sommaire (il est à gauche)."""
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire")

    assert page.status_code == 200
    lu = texte(page)
    assert "Là où vous en êtes" in lu
    assert "Étape 3 sur 5" in lu
    assert "Revue de littérature" in lu           # l'étape ouverte, mise en avant
    assert "Votre avancement" in lu
    assert "Sujet" in lu                          # les étapes vivent dans la barre latérale


def test_le_parcours_montre_le_quota_restant(site):
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire")

    assert "Il vous reste" in page.text
    assert "17" in page.text


def test_mes_memoires_liste_les_dossiers_de_l_etudiant(site):
    client, _, reglages = site
    connecter(client, reglages, "etudiant-1")
    ouvrir_memoire(reglages, "etudiant-1", "premier-memoire", "Le télétravail")
    ouvrir_memoire(reglages, "etudiant-1", "second-memoire", "La motivation")

    page = client.get("/mes-memoires")

    assert "Le télétravail" in page.text
    assert "La motivation" in page.text


# ------------------------------------------------------------------- l'étape
def test_l_etape_montre_inconnues_limites_questions_et_verdict(site):
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire/etape")

    lu = texte(page)
    assert page.status_code == 200
    assert "Ce que l'on ne sait pas encore" in lu
    assert "Aucune donnée sur les PME d'Abidjan." in lu
    assert "Limites de cette proposition" in lu
    assert "Questions posées par l'accompagnement" in lu
    assert "Vérification indépendante" in lu
    assert "Je valide cette étape" in page.text
    assert "Demander une révision" in page.text


def test_une_cle_technique_n_apparait_jamais_a_l_ecran(site):
    """Ce qui sert en interne ne doit jamais être montré à l'étudiant."""
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire/etape")

    assert "internal_metadata_should_never_be_shown" not in page.text


def test_une_liste_d_objets_devient_des_fiches_pas_des_titres_repete(site):
    """Trouvé à l'écran : une liste d'objets s'affichait en titres géants répétés."""
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire/etape")

    assert '<p class="fiche-titre">Productivité mesurée</p>' in page.text


def test_une_sortie_d_agent_ne_peut_pas_devenir_du_code(site):
    """Un texte hostile produit par un agent doit rester du TEXTE, jamais du HTML actif."""
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire/etape")

    assert "<script>alert" not in page.text
    assert "&lt;script&gt;" in page.text


def test_la_decision_transmet_le_choix_a_l_orchestrateur(site):
    client, simule, _ = _preparer(site)

    reponse = client.post("/memoire/mon-memoire/etape/decision", data={
        "csrf": csrf_du(client), "n": 3, "decision": "accepted", "commentaire": ""})

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/memoire/mon-memoire"
    assert ("POST", "/dossiers/etudiant-1/mon-memoire/decision") in simule.appels


def test_une_decision_sans_jeton_est_refusee(site):
    client, simule, _ = _preparer(site)
    avant = len(simule.appels)

    reponse = client.post("/memoire/mon-memoire/etape/decision", data={
        "csrf": "faux", "decision": "accepted"})

    assert reponse.status_code == 303
    assert len(simule.appels) == avant  # l'orchestrateur n'a rien reçu


def test_le_lancement_d_une_etape_passe_par_l_orchestrateur(site):
    client, simule, _ = _preparer(site)

    reponse = client.post("/memoire/mon-memoire/etape/lancer", data={"csrf": csrf_du(client)})

    assert reponse.status_code == 303
    assert ("POST", "/dossiers/etudiant-1/mon-memoire/etape") in simule.appels


# --------------------------------------------------------------- documents
def test_les_documents_et_la_bibliographie_sont_telechargeables(site):
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire/documents")
    assert "Un article" in page.text
    assert "format=bibtex" in page.text

    fichier = client.get("/memoire/mon-memoire/documents/d1/fichier")
    assert fichier.status_code == 200
    assert fichier.headers["content-type"] == "application/pdf"

    biblio = client.get("/memoire/mon-memoire/bibliographie?format=bibtex")
    assert biblio.status_code == 200
    assert "bibliographie.bib" in biblio.headers["content-disposition"]


# ------------------------------------------------------------------- erreurs
def test_un_orchestrateur_en_panne_est_annonce_en_francais(site):
    """Une panne est une erreur SERVEUR : le code HTTP doit le dire (500), et jamais 200.

    Un 200 sur une page d'erreur trompait tout le monde — navigateur, moteur de recherche,
    supervision. La page reste la même ; seul le code devient honnête.
    """
    client, simule, _ = _preparer(site)
    simule.en_panne = True

    page = client.get("/memoire/mon-memoire")

    assert page.status_code == 500
    assert "ne répond pas pour le moment" in page.text
    assert "Traceback" not in page.text


def test_une_ressource_inconnue_est_annoncee_en_404(site):
    """Une ressource qui n'existe pas est un 404 — distinct d'une panne (500)."""
    client, simule, _ = _preparer(site)
    simule.en_panne = True
    simule.statut_erreur = 404

    page = client.get("/memoire/mon-memoire")

    assert page.status_code == 404
    assert "Revenir à mes mémoires" in page.text


def test_le_client_conserve_le_code_http_de_l_erreur():
    """Le code remonte du client : 404 (ressource inconnue) ≠ 500 (panne), jamais 200."""
    from site_web.clients.orchestrateur import Orchestrateur

    assert Orchestrateur._traduire(404, "", "http://127.0.0.1:8000/x").statut == 404
    assert Orchestrateur._traduire(500, "", "http://127.0.0.1:8000/x").statut == 500
    assert Orchestrateur._traduire(429, "", "http://127.0.0.1:8000/x").statut == 429


def test_l_etudiant_est_redirige_vers_la_connexion_s_il_expire(site):
    client, _, reglages = _preparer(site)
    client.cookies.clear()

    reponse = client.get("/memoire/mon-memoire")

    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/connexion"


# --------------------------------------------------- frontière d'architecture
def test_le_site_ne_connait_aucun_agent():
    """LA règle d'architecture : le site ne parle qu'à l'orchestrateur.

    Si ce test casse, c'est qu'un raccourci a été pris : quelqu'un a branché le site directement
    sur un agent. C'est exactement ce que cette architecture interdit.
    """
    racine = pathlib.Path(__file__).resolve().parents[2] / "src" / "site_web"
    interdits = ("import orchestrator", "from orchestrator", "literature_review_agent",
                 "methodology_agent", "subject_agent", "discussion_agent", "global_verifier")
    for fichier in racine.rglob("*.py"):
        texte = fichier.read_text(encoding="utf-8")
        for interdit in interdits:
            assert interdit not in texte, f"{fichier.name} mentionne « {interdit} »"


def test_le_site_ecrit_sur_la_console_du_serveur_et_non_dans_la_page(site):
    """Rien de la mécanique interne ne doit fuir dans la réponse HTML."""
    client, _, _ = _preparer(site)

    page = client.get("/memoire/mon-memoire")

    for fuite in ("http://127.0.0.1", "/root/", "sqlite", "Traceback", "orchestrateur_url"):
        assert fuite not in page.text, fuite
