"""API interne de l'orchestrateur (aucun agent lancé : les routes sont testées sans appel réseau)."""

import json

from fastapi.testclient import TestClient

from orchestrator.main import app


def _client(settings):
    """Client de test SANS exécuter le cycle de vie : aucun état réel n'est touché."""
    app.state.settings = settings
    return TestClient(app)


def test_sante(settings):
    assert _client(settings).get("/health").json()["status"] == "ok"


def test_creation_puis_consultation(settings):
    client = _client(settings)
    reponse = client.post("/dossiers/etu-api/sess-api",
                          json={"sujet": "Le télétravail et la productivité",
                                "sujet_contexte": {"discipline": "Sciences de gestion"}})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["etape_ouverte"] == 1
    assert corps["libelle"] == "Sujet"

    consultation = client.get("/dossiers/etu-api/sess-api").json()
    assert consultation["sujet"] == "Le télétravail et la productivité"
    assert consultation["quota_restant"] == settings.analyses_par_jour


def test_la_creation_n_ecrase_pas_un_dossier_existant(settings):
    client = _client(settings)
    client.post("/dossiers/etu2/s2", json={"sujet": "Premier sujet"})
    seconde = client.post("/dossiers/etu2/s2", json={"sujet": "Autre sujet"})
    assert seconde.json()["sujet"] == "Premier sujet"


def test_dossier_inconnu_renvoie_404(settings):
    reponse = _client(settings).get("/dossiers/personne/inconnu")
    assert reponse.status_code == 404
    assert reponse.json()["detail"]["error"] == "DOSSIER_INCONNU"


def test_decision_sans_proposition_renvoie_409(settings):
    client = _client(settings)
    client.post("/dossiers/etu3/s3", json={"sujet": "Sujet"})
    reponse = client.post("/dossiers/etu3/s3/decision", json={"decision": "accepted"})
    assert reponse.status_code == 409
    assert reponse.json()["detail"]["error"] == "ETAPE_NON_AUTORISEE"


def test_decision_inconnue_renvoie_400(settings):
    client = _client(settings)
    client.post("/dossiers/etu4/s4", json={"sujet": "Sujet"})
    reponse = client.post("/dossiers/etu4/s4/decision", json={"decision": "peut_etre"})
    assert reponse.status_code == 400
    assert reponse.json()["detail"]["error"] == "DECISION_INVALIDE"


def test_champ_inconnu_dans_le_corps_refuse(settings):
    """Une entrée non prévue est refusée : on ne devine rien sur ce que la plateforme veut dire."""
    reponse = _client(settings).post("/dossiers/etu5/s5",
                                     json={"sujet": "Sujet", "champ_en_trop": 1})
    assert reponse.status_code == 422


def test_le_contexte_accepte_une_chaine(settings):
    """Le contexte d'un étudiant est souvent du TEXTE : le site envoie une CHAÎNE, et il a raison.

    Vérifié en exécution réelle : envoyer une chaîne renvoyait `HTTP 422 dict_type`. Une chaîne est
    désormais acceptée et encapsulée en OBJET (`{"contexte": "…"}`) pour que le pipeline continue
    de recevoir un objet — jamais du texte brut.
    """
    client = _client(settings)
    reponse = client.post("/dossiers/etu-chaine/s-chaine",
                          json={"sujet": "Le télétravail et la productivité",
                                "sujet_contexte": "Je travaille sur les PME d'Abidjan."})
    assert reponse.status_code == 200

    from orchestrator.storage import state

    dossier = state.dossier(settings.state_db, "etu-chaine", "s-chaine")
    assert json.loads(dossier["contexte"]) == {"contexte": "Je travaille sur les PME d'Abidjan."}


def test_le_contexte_accepte_toujours_un_objet(settings):
    """Un objet bien formé est gardé TEL QUEL : la tolérance n'écrase pas la forme structurée."""
    client = _client(settings)
    reponse = client.post("/dossiers/etu-objet/s-objet",
                          json={"sujet": "Sujet",
                                "sujet_contexte": {"discipline": "Sciences de gestion"}})
    assert reponse.status_code == 200

    from orchestrator.storage import state

    dossier = state.dossier(settings.state_db, "etu-objet", "s-objet")
    assert json.loads(dossier["contexte"]) == {"discipline": "Sciences de gestion"}


def test_le_contexte_refuse_une_forme_invalide(settings):
    """Ni texte ni objet : on REFUSE (422). La tolérance ne doit pas tout accepter en silence."""
    reponse = _client(settings).post("/dossiers/etu-liste/s-liste",
                                     json={"sujet": "Sujet", "sujet_contexte": ["a", "b"]})
    assert reponse.status_code == 422


def test_lancement_sans_agent_renvoie_une_erreur_expliquee(settings):
    """Aucun agent n'écoute : l'erreur doit être EXPLIQUÉE, jamais une trace technique.

    Le test est rendu HERMÉTIQUE : il pointe vers un port où rien n'écoute. Sans cela, il
    dépendrait de ce qui tourne sur la machine — un vrai agent lancé sur 8010 faisait réussir le
    lancement et échouer le test.
    """
    import dataclasses

    from orchestrator.pipeline import registry

    registry.reinitialiser_cache()
    settings = dataclasses.replace(
        settings, etapes=tuple(dataclasses.replace(etape, port=65533)
                               for etape in settings.etapes))
    client = _client(settings)
    client.post("/dossiers/etu6/s6", json={"sujet": "Sujet"})
    reponse = client.post("/dossiers/etu6/s6/etape")
    assert reponse.status_code in (400, 429)
    detail = reponse.json()["detail"]
    assert detail["error"] in ("AGENT_INDISPONIBLE", "AGENT_EN_ECHEC", "QUOTA_DEPASSE")
    assert "http" not in detail["message"]


def test_la_carte_publique_du_parcours_est_numerotee_sans_trou(settings):
    """Ce qui est montré à un VISITEUR : les étapes, numérotées 1..N sans trou.

    Le numéro interne saute l'étape réservée (… 11, puis 13) : la position affichée, elle, doit
    rester continue, sinon la dernière étape s'annoncerait « étape 13 sur 12 ».
    """
    reponse = _client(settings).get("/parcours")

    assert reponse.status_code == 200
    etapes = reponse.json()["etapes"]
    assert len(etapes) == len(settings.etapes)
    assert [etape["position"] for etape in etapes] == list(range(1, len(etapes) + 1))


def test_la_carte_publique_ne_revele_rien_d_interne(settings):
    """Un visiteur voit les étapes — ni les agents, ni leurs adresses, ni leurs ports.

    `resume` est PUBLIC : c'est la phrase qui dit à l'étudiant, en français, ce que l'étape lui
    demandera. On liste donc ce qui est INTERDIT plutôt que la liste exacte des clés : ajouter un
    champ public ne doit pas casser ce test, mais laisser fuiter un champ interne doit le casser.
    """
    etapes = _client(settings).get("/parcours").json()["etapes"]
    publiques = {"numero", "position", "libelle", "resume"}
    interdites = {"agent", "port", "prefixe", "route_analyse", "upstream", "champs"}

    for etape in etapes:
        assert set(etape) <= publiques, f"champ public non prévu : {set(etape) - publiques}"
        assert not (set(etape) & interdites), f"champ interne divulgué : {set(etape) & interdites}"
        assert "port" not in etape
        assert "prefixe" not in etape
