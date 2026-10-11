"""La coquille d'application : le parcours EST la navigation, et le dynamisme reste sûr.

Structure retenue (inspirée des meilleurs outils : Linear, Notion) — barre latérale persistante
avec les douze étapes, volet de contenu, en-tête illustré, recherche rapide. Et une règle qui ne
bouge pas : le dynamisme ne doit JAMAIS faire entrer du code étranger dans la page.
"""

import re

from site_helpers import connecter, ouvrir_memoire


def _connecte(site, session="mon-memoire"):
    client, simule, reglages = site
    connecter(client, reglages, "etudiante@exemple.com")
    ouvrir_memoire(reglages, "etudiante@exemple.com", session)
    return client, simule, reglages


# ------------------------------------------------------------------- structure
def test_les_etapes_sont_dans_la_barre_laterale(site):
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire")

    assert page.status_code == 200
    assert 'class="laterale"' in page.text
    assert page.text.count('class="laterale-etape') >= 5
    assert "Les étapes" in page.text


def test_l_avancement_est_visible_d_un_coup_d_oeil(site):
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text

    assert "étapes validées" in page
    assert "data-anneau=" in page, "l'anneau de progression doit être alimenté"


def test_une_etape_fermee_n_est_pas_un_lien(site):
    """On ne propose pas d'ouvrir une porte qui n'est pas encore ouverte."""
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text

    assert "laterale-etape fermee" in page


def test_le_tableau_de_bord_ne_repete_pas_la_liste_des_etapes(site):
    """La liste vit dans la barre latérale : la page montre l'action, pas un second sommaire."""
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text

    assert "Là où vous en êtes" in page
    assert "Mes ressources" in page
    assert 'class="sommaire"' not in page


def test_la_recherche_rapide_est_offerte(site):
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text

    assert "data-ouvre-palette" in page
    assert "data-palette" in page


def test_l_en_tete_porte_une_image(site):
    client, _, reglages = site
    connecter(client, reglages, "etudiante@exemple.com")

    page = client.get("/mes-memoires").text

    assert "illustrations/bandeau.svg" in page
    assert "logo.svg" in page


def test_la_barre_laterale_suit_sur_toutes_les_pages_du_memoire(site):
    client, _, _ = _connecte(site)

    for chemin in ("/memoire/mon-memoire", "/memoire/mon-memoire/etape",
                   "/memoire/mon-memoire/documents", "/memoire/mon-memoire/journal"):
        page = client.get(chemin)
        assert page.status_code == 200, chemin
        assert 'class="laterale"' in page.text, chemin


# ------------------------------------------------------------------- sécurité
def test_le_site_n_a_qu_un_seul_script_et_il_est_a_nous(site):
    """Aucun script en ligne, aucun script étranger : la politique n'autorise que nos fichiers."""
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text
    balises = re.findall(r"<script[^>]*>", page)

    assert len(balises) == 1
    for balise in balises:
        source = re.search(r'src="([^"]+)"', balise)
        assert source, balise
        assert source.group(1).rstrip("/").endswith("/static/app.js"), balise
        # Aucun domaine étranger : le script vient de chez nous, jamais d'ailleurs.
        from urllib.parse import urlparse

        assert urlparse(source.group(1)).netloc in ("", "testserver"), balise


def test_la_palette_de_commandes_est_masquee_par_defaut(site):
    """Défaut réel vu à l'écran : un `display` de la feuille écrasait l'attribut `hidden`, et la
    palette restait ouverte en permanence par-dessus la page."""
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text
    feuille = client.get("/static/style.css").text

    balise = re.search(r"<div class=\"palette\"[^>]*>", page)
    assert balise and "hidden" in balise.group(0), balise
    assert ".palette[hidden]" in feuille, "l'attribut hidden doit l'emporter sur le display"


def test_la_barre_laterale_affiche_les_positions_pas_les_numeros_internes(site):
    """L'étudiant lit une suite continue (1..N) : les numéros internes ne le concernent pas."""
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text

    assert '<span class="laterale-puce">5</span>' in page      # dernière position du parcours
    assert '<span class="laterale-puce">13</span>' not in page  # numéro interne d'une étape


def test_le_script_est_bien_servi(site):
    client, _, _ = site

    reponse = client.get("/static/app.js")

    assert reponse.status_code == 200
    assert "javascript" in reponse.headers["content-type"]


def test_le_contenu_reste_visible_sans_javascript(site):
    """Les effets d'apparition ne s'activent que si le script tourne (classe « js » posée par lui)."""
    client, _, _ = _connecte(site)

    page = client.get("/memoire/mon-memoire").text

    # La règle d'invisibilité est conditionnée à .js, jamais appliquée d'office.
    assert "html.js" not in page
    feuille = client.get("/static/style.css").text
    assert ".js [data-apparait]" in feuille
    assert "\n[data-apparait] {" not in feuille
