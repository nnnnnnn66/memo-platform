"""Registre des agents : l'orchestrateur doit CONNAÎTRE ses agents (leçon du lab).

Ces tests n'ouvrent AUCUNE connexion réseau : un interrogateur simulé remplace les appels HTTP.
"""

import pytest

from orchestrator.core.errors import EtatErreur, OrchestratorError
from orchestrator.pipeline import campaign, registry


def _fiche(etape, en_ligne=True, capacites=None, entrees=None, etape_declaree=None):
    """Fiche telle que la produirait un agent en ligne (ou éteint)."""
    return {
        "agent": etape.agent,
        "etape": etape.numero,
        "libelle": etape.libelle,
        "adresse": f"127.0.0.1:{etape.port}",
        "en_ligne": en_ligne,
        "etat_sante": "healthy" if en_ligne else "",
        "capacites": capacites if capacites is not None else ["capacite_de_test"],
        "role": "rôle déclaré",
        "nom_declare": etape.libelle,
        "entrees_requises": list(entrees if entrees is not None else etape.upstream),
        "necessite_reseau": False,
        "etape_declaree": etape.numero if etape_declaree is None else etape_declaree,
        "probleme": "" if en_ligne else "injoignable (URLError)",
    }


def test_registre_liste_toutes_les_etapes(settings):
    fiches = registry.registre(settings, interrogateur=lambda etape: _fiche(etape))
    assert len(fiches) == len(settings.etapes)
    assert all(fiche["en_ligne"] for fiche in fiches)


def test_agents_hors_ligne_detectes(settings):
    def interrogateur(etape):
        # L'agent de l'étape 3 est éteint, les autres répondent.
        return _fiche(etape, en_ligne=etape.numero != 3)

    eteints = registry.agents_hors_ligne(settings, interrogateur=interrogateur)
    assert [fiche["etape"] for fiche in eteints] == [3]
    assert "injoignable" in eteints[0]["probleme"]


def test_lancement_refuse_si_l_agent_est_eteint(settings, agent):
    """Refus EXPLIQUÉ, avant tout appel — et sans consommer le quota."""
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    with pytest.raises(OrchestratorError) as info:
        campaign.lancer_etape(
            settings, "etu1", "s1", transport=agent,
            interrogateur=lambda etape: _fiche(etape, en_ligne=False))
    assert info.value.etat == EtatErreur.AGENT_INDISPONIBLE
    assert "éteint" in info.value.message_etudiant
    assert agent.appels == []                     # aucun appel à l'agent
    from orchestrator.pipeline import quota
    assert quota.restant(settings.state_db, "etu1", settings.analyses_par_jour) == \
        settings.analyses_par_jour               # quota intact


def test_lancement_autorise_si_l_agent_repond(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    resultat = campaign.lancer_etape(
        settings, "etu1", "s1", transport=agent,
        interrogateur=lambda etape: _fiche(etape, en_ligne=True))
    assert resultat["etape"] == 1


def test_desaccord_entre_carte_et_agent_est_signale(settings):
    """Un agent qui se déclare ailleurs, ou qui attend une entrée non prévue, doit être SIGNALÉ :
    c'est exactement ce genre de désaccord qui casse une chaîne en silence."""
    etape = settings.par_numero[5]
    problemes = registry.ecarts(etape, {"etape": 6, "entrees_requises": ["upstream_inconnu"]})
    assert any("déclare l'étape 6" in p for p in problemes)
    assert any("upstream_inconnu" in p for p in problemes)
    # Accord parfait : aucun écart signalé.
    assert registry.ecarts(
        etape, {"etape": 5, "entrees_requises": sorted(etape.upstream)}) == []


def test_interrogation_reelle_detecte_le_desaccord(settings, monkeypatch):
    """Chemin réel : /health puis /capabilities sont lus, puis la cohérence est contrôlée."""
    def faux_lire(url, timeout):
        if url.endswith("/health"):
            return {"status": "healthy"}
        return {"etape": 6, "capacites": ["x"], "role": "r",
                "entrees_requises": ["upstream_inconnu"]}

    monkeypatch.setattr(registry, "_lire", faux_lire)
    fiche = registry.interroger_agent(settings.par_numero[5], "127.0.0.1")
    assert fiche["en_ligne"] is True
    assert "déclare l'étape 6" in fiche["probleme"]


def test_agent_en_ligne_mais_muet_est_signale(settings, monkeypatch):
    """Un agent qui répond à /health mais ne se déclare pas a une capacité INCONNUE : on le dit."""
    def faux_lire(url, timeout):
        if url.endswith("/health"):
            return {"status": "healthy"}
        raise ValueError("pas de JSON")

    monkeypatch.setattr(registry, "_lire", faux_lire)
    fiche = registry.interroger_agent(settings.par_numero[1], "127.0.0.1")
    assert fiche["en_ligne"] is True
    assert fiche["capacites"] == []
    assert fiche["role"] == ""                    # rien n'est inventé
    assert "se déclare mal" in fiche["probleme"]


def test_cache_evite_des_interrogations_repetees(settings):
    compteur = {"n": 0}

    def interrogateur(etape):
        compteur["n"] += 1
        return _fiche(etape)

    registry.reinitialiser_cache()
    # L'interrogateur injecté n'est jamais mis en cache (les tests restent déterministes)…
    registry.registre(settings, interrogateur=interrogateur)
    registry.registre(settings, interrogateur=interrogateur)
    assert compteur["n"] == 2 * len(settings.etapes)
