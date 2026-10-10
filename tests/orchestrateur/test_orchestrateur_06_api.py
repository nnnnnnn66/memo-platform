"""API interne de l'orchestrateur (aucun agent lancé : les routes sont testées sans appel réseau)."""

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


def test_lancement_sans_agent_renvoie_une_erreur_expliquee(settings):
    """Aucun agent n'écoute : l'erreur doit être EXPLIQUÉE, jamais une trace technique."""
    client = _client(settings)
    client.post("/dossiers/etu6/s6", json={"sujet": "Sujet"})
    reponse = client.post("/dossiers/etu6/s6/etape")
    assert reponse.status_code in (400, 429)
    detail = reponse.json()["detail"]
    assert detail["error"] in ("AGENT_INDISPONIBLE", "AGENT_EN_ECHEC", "QUOTA_DEPASSE")
    assert "http" not in detail["message"]
