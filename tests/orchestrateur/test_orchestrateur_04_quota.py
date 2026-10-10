"""Quota quotidien : le portefeuille du porteur ne doit jamais partir en fumée."""

import dataclasses

import pytest

from orchestrator.core.errors import EtatErreur, OrchestratorError
from orchestrator.pipeline import campaign, quota
from orchestrator.storage import state


def test_chaque_analyse_consomme_le_quota(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    resultat = campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    assert resultat["quota_restant"] == settings.analyses_par_jour - 1
    assert state.quota_du_jour(settings.state_db, "etu1", quota.jour_courant()) == 1


def test_quota_atteint_refuse_AVANT_d_appeler_l_agent(settings, agent):
    """Refuser après l'appel ne protégerait rien : le contrôle est fait en amont."""
    serre = dataclasses.replace(settings, analyses_par_jour=1)
    campaign.creer_dossier(serre, "etu1", "s1", "Sujet")
    campaign.lancer_etape(serre, "etu1", "s1", transport=agent)
    campaign.decider(serre, "etu1", "s1", "modified", transport=agent)   # étape relançable

    appels_avant = len(agent.appels)
    with pytest.raises(OrchestratorError) as info:
        campaign.lancer_etape(serre, "etu1", "s1", transport=agent)
    assert info.value.etat == EtatErreur.QUOTA_DEPASSE
    assert len(agent.appels) == appels_avant          # aucun appel réseau de plus
    # Le message parle à l'étudiant et rassure sur la conservation du dossier.
    assert "quotidienne" in info.value.message_etudiant
    assert "conservé" in info.value.message_etudiant


def test_le_quota_ne_bloque_pas_la_consultation(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    etat = campaign.etat(settings, "etu1", "s1")
    assert etat["quota_restant"] == settings.analyses_par_jour - 1
    assert etat["quota_max"] == settings.analyses_par_jour


def test_quota_independant_par_etudiant(settings, agent):
    campaign.creer_dossier(settings, "etuA", "sA", "Sujet A")
    campaign.creer_dossier(settings, "etuB", "sB", "Sujet B")
    campaign.lancer_etape(settings, "etuA", "sA", transport=agent)
    assert state.quota_du_jour(settings.state_db, "etuA", quota.jour_courant()) == 1
    assert state.quota_du_jour(settings.state_db, "etuB", quota.jour_courant()) == 0


def test_quota_reinitialise_le_lendemain(settings):
    """Le quota est journalier : la consommation d'hier ne bloque pas aujourd'hui."""
    state.incrementer_quota(settings.state_db, "etu1", "2000-01-01")
    assert quota.restant(settings.state_db, "etu1", 5, "2000-01-01") == 4
    assert quota.restant(settings.state_db, "etu1", 5, "2000-01-02") == 5
