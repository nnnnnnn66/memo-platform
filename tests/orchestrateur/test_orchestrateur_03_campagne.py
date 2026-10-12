"""Le parcours : une seule étape ouverte, un pont réel, et aucune validation sans décision humaine."""

import pytest

from orchestrator.core.errors import EtatErreur, OrchestratorError
from orchestrator.pipeline import campaign
from orchestrator.storage import state

from orchestrateur_helpers import avancer


def test_premiere_etape_ouverte_a_la_creation(settings):
    etat = campaign.creer_dossier(settings, "etu1", "s1", "Le télétravail et la productivité")
    assert etat["etape_ouverte"] == 1
    assert etat["libelle"] == "Sujet"
    assert etat["statut"] == state.STATUT_A_FAIRE
    assert etat["quota_restant"] == settings.analyses_par_jour


def test_lancer_une_etape_produit_une_proposition(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet de test")
    resultat = campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    assert resultat["etape"] == 1
    assert resultat["statut"] == state.STATUT_PROPOSEE
    assert resultat["verdict"] == "verified"
    # L'agent appelé est bien celui de l'étape 1, sur SON port.
    assert "8010" in agent.appels[-1][0]


def test_aucune_validation_sans_decision_humaine(settings, agent):
    """Le point le plus important : l'agent ne valide jamais à la place de l'étudiant."""
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet de test")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    etat = campaign.etat(settings, "etu1", "s1")
    assert etat["statut"] == state.STATUT_PROPOSEE
    assert etat["etape_ouverte"] == 1          # l'étape 2 reste FERMÉE
    assert etat["decision"] == ""


def test_la_decision_humaine_ouvre_l_etape_suivante(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet de test")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    resultat = campaign.decider(settings, "etu1", "s1", "accepted", transport=agent)
    assert resultat["statut"] == state.STATUT_VALIDEE
    assert resultat["etape_suivante"] == 2
    assert resultat["libelle_suivant"] == "Problème de recherche"


def test_le_pont_transmet_la_sortie_REELLE_de_l_etape_precedente(settings, agent):
    """La sortie de l'étape 1 doit arriver TELLE QUELLE dans `upstream_subject` de l'étape 2."""
    campaign.creer_dossier(settings, "etu1", "s1", "Le télétravail et la productivité")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    production_etape1 = agent.resultat

    campaign.decider(settings, "etu1", "s1", "accepted", transport=agent)
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)      # étape 2

    entree2 = agent.derniere_entree
    assert entree2["upstream_subject"] == production_etape1
    assert "8020" in agent.appels[-1][0]
    # La sortie de l'étape 2 n'est pas encore validée : l'étape 3 attend la décision humaine.
    assert campaign.etat(settings, "etu1", "s1")["etape_ouverte"] == 2


def test_une_proposition_en_attente_n_est_pas_recalculee(settings, agent):
    """Relancer une étape déjà proposée brûlerait des tokens pour rien : on refuse."""
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    with pytest.raises(OrchestratorError) as info:
        campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    assert info.value.etat == EtatErreur.ETAPE_NON_AUTORISEE
    assert len(agent.appels) == 1        # aucun appel supplémentaire


def test_decider_sans_proposition_est_refuse(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    with pytest.raises(OrchestratorError) as info:
        campaign.decider(settings, "etu1", "s1", "accepted", transport=agent)
    assert info.value.etat == EtatErreur.ETAPE_NON_AUTORISEE


def test_decision_inconnue_refusee(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    with pytest.raises(OrchestratorError) as info:
        campaign.decider(settings, "etu1", "s1", "peut_etre", transport=agent)
    assert info.value.etat == EtatErreur.DECISION_INVALIDE


def test_demander_une_revision_laisse_l_etape_ouverte(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    resultat = campaign.decider(settings, "etu1", "s1", "modified", "à revoir",
                                transport=agent)
    assert resultat["statut"] == state.STATUT_A_REVISER
    assert resultat["etape_suivante"] == 1        # on reste sur l'étape 1
    # L'étape peut être relancée après une demande de révision.
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    assert campaign.etat(settings, "etu1", "s1")["statut"] == state.STATUT_PROPOSEE


def test_avancement_regulier_jusqu_a_la_verification_globale(settings, agent):
    """Le parcours complet (hors agents réels) : 1 → 10, la vérification globale, puis la conclusion."""
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    avancer(settings, "etu1", "s1", agent, nombre=10)
    etat = campaign.etat(settings, "etu1", "s1")
    assert etat["etape_ouverte"] == 13
    assert etat["libelle"] == "Vérification globale de la cohérence"
    # Elle reçoit les sorties des étapes 1 à 10 — PAS la conclusion, qui vient après elle.
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    entree = agent.derniere_entree
    assert sorted(k for k in entree if k.startswith("upstream_")) == [
        "upstream_hypotheses", "upstream_literature",
        "upstream_methodology", "upstream_methodology_diagnostic", "upstream_objectives",
        "upstream_problem", "upstream_problematic", "upstream_question", "upstream_results",
        "upstream_subject"]
    assert "upstream_conclusion" not in entree
    assert "8130" in agent.appels[-1][0]

    # Après la vérification vient la CONCLUSION, dernière étape du parcours.
    campaign.decider(settings, "etu1", "s1", "accepted", transport=agent)
    etat = campaign.etat(settings, "etu1", "s1")
    assert etat["etape_ouverte"] == 11
    assert etat["libelle"] == "Conclusion"
