"""Sécurité et honnêteté : isolation des dossiers, pannes déclarées, messages sans jargon."""

import pytest

from orchestrator.core.errors import EtatErreur, OrchestratorError
from orchestrator.pipeline import campaign
from orchestrator.storage import state


def test_un_etudiant_ne_voit_que_son_dossier(settings, agent):
    campaign.creer_dossier(settings, "etuA", "sA", "Sujet confidentiel A")
    campaign.creer_dossier(settings, "etuB", "sB", "Sujet B")
    campaign.lancer_etape(settings, "etuA", "sA", transport=agent)

    etat_b = campaign.etat(settings, "etuB", "sB")
    assert etat_b["sujet"] == "Sujet B"
    assert etat_b["statut"] == state.STATUT_A_FAIRE
    assert etat_b["avancement"] == []           # aucun résultat de l'étudiant A
    # Une session différente du même étudiant est un AUTRE dossier.
    with pytest.raises(OrchestratorError):
        campaign.etat(settings, "etuA", "autre-session")


def test_dossier_inconnu_ne_cree_rien_implicitement(settings):
    with pytest.raises(OrchestratorError) as info:
        campaign.etat(settings, "inconnu", "s")
    assert info.value.etat == EtatErreur.DOSSIER_INCONNU


def test_un_echec_d_agent_est_declare_et_n_invente_rien(settings):
    """Agent injoignable : l'étape est marquée en échec, rien n'est validé, le dossier reste."""
    def transport_en_panne(url, charge):
        raise OrchestratorError(EtatErreur.AGENT_INDISPONIBLE,
                                "Le service de cette étape ne répond pas pour le moment.",
                                "test")

    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    with pytest.raises(OrchestratorError):
        campaign.lancer_etape(settings, "etu1", "s1", transport=transport_en_panne)

    ligne = state.statut(settings.state_db, "etu1", "s1", 1)
    assert ligne["statut"] == state.STATUT_ECHEC
    assert ligne["verdict"] == "echec"
    assert state.sortie_validee(settings.state_db, "etu1", "s1", 1) is None
    # Le dossier existe toujours et l'étape reste ouverte : l'étudiant peut réessayer.
    assert campaign.etat(settings, "etu1", "s1")["etape_ouverte"] == 1


def test_le_message_etudiant_ne_contient_pas_de_jargon(settings):
    """Ce qui est affiché à l'étudiant ne doit contenir ni chemin, ni URL, ni trace."""
    erreur = OrchestratorError(EtatErreur.AGENT_INDISPONIBLE,
                               "Le service de cette étape ne répond pas pour le moment.",
                               "URLError sur http://127.0.0.1:8030/literature/review")
    assert "http" not in erreur.message_etudiant
    assert "/" not in erreur.message_etudiant
    assert "Traceback" not in erreur.message_etudiant
    # Le détail technique reste disponible pour les journaux, séparément.
    assert "127.0.0.1" in erreur.detail


def test_la_decision_enregistree_est_tracee(settings, agent):
    campaign.creer_dossier(settings, "etu1", "s1", "Sujet")
    campaign.lancer_etape(settings, "etu1", "s1", transport=agent)
    campaign.decider(settings, "etu1", "s1", "accepted", "sujet conforme à mon projet",
                     transport=agent)
    ligne = state.statut(settings.state_db, "etu1", "s1", 1)
    assert ligne["decision"] == "accepted"
    assert ligne["commentaire"] == "sujet conforme à mon projet"
    assert state.sortie_validee(settings.state_db, "etu1", "s1", 1) == agent.resultat
