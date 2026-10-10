"""La page d'accueil publique : on n'arrive plus devant une porte fermée.

Elle sert deux choses : dire à un visiteur ce que fait la plateforme (et ce qu'elle ne fait pas),
et lui donner par où entrer. Elle ne doit JAMAIS dépendre d'un service pour rester présentable.
"""

from site_helpers import connecter

from site_web import main as main_site


def test_un_visiteur_arrive_sur_l_accueil_et_non_sur_la_connexion(site):
    client, _, _ = site

    page = client.get("/")

    assert page.status_code == 200
    assert "connexion-page" not in page.text, "on ne doit pas tomber sur la page de connexion"
    assert "Créer mon accès" in page.text


def test_l_accueil_dit_ce_que_la_plateforme_fait_et_ne_fait_pas(site):
    client, _, _ = site

    page = client.get("/").text

    assert "Ce qu'elle fait" in page
    assert "Ce qu'elle ne fait pas" in page
    assert "n'écrit pas votre mémoire à votre place" in page
    assert "sans votre clic" in page


def test_l_accueil_montre_les_etapes_du_parcours(site):
    client, simule, _ = site

    page = client.get("/").text

    assert "Revue de littérature" in page
    assert "Problème de recherche" in page
    assert ("GET", "/parcours") in simule.appels


def test_l_accueil_ne_reinterroge_pas_le_service_a_chaque_visite(site):
    """La carte est la même pour tous : on la garde un instant au lieu de frapper à chaque visite."""
    client, simule, _ = site
    client.get("/")
    appels_apres_la_premiere = len(simule.appels)

    client.get("/")

    assert len(simule.appels) == appels_apres_la_premiere


def test_l_accueil_reste_presentable_si_l_orchestrateur_est_eteint(site):
    """Aucune page publique ne doit afficher une erreur technique."""
    client, simule, _ = site
    simule.en_panne = True
    main_site._CACHE_PARCOURS.update(quand=0.0, etapes=[])

    page = client.get("/")

    assert page.status_code == 200
    assert "Un mémoire ne s'improvise pas" in page.text
    assert "Créer mon accès" in page.text
    assert "Traceback" not in page.text
    assert "ne répond pas" not in page.text


def test_l_accueil_parle_a_l_etudiant_deja_connecte(site):
    client, _, reglages = site
    connecter(client, reglages, "etudiante@exemple.com")

    page = client.get("/")

    assert "Reprendre mon mémoire" in page.text
    assert "Mes mémoires" in page.text


def test_les_pages_d_entree_ramenent_a_l_accueil(site):
    client, _, _ = site

    assert 'href="/">← Retour à l\'accueil' in client.get("/connexion").text
    assert 'href="/">← Retour à l\'accueil' in client.get("/inscription").text


def test_l_accueil_ne_montre_rien_de_technique(site):
    client, _, _ = site

    page = client.get("/").text

    for fuite in ("http://127.0.0.1", "/root/", "sqlite", "orchestrateur", "agent"):
        assert fuite not in page.lower(), fuite
