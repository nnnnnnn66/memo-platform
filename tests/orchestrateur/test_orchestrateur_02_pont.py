"""Le pont entre étapes : ce qui part vers un agent est-il RÉELLEMENT ce que l'amont a produit ?"""

import pytest

from orchestrator.core.errors import EtatErreur, OrchestratorError
from orchestrator.pipeline import handoff


def test_entree_porte_les_champs_de_base_du_dossier(settings):
    dossier = {"sujet": "Le télétravail et la productivité", "contexte": {"discipline": "Gestion"}}
    etape = settings.par_numero[1]
    entree = handoff.construire_entree(settings, "etu1", "sess1", etape, dossier, {})
    assert entree["student_id"] == "etu1"
    assert entree["session_id"] == "sess1"
    assert entree["subject_text"] == "Le télétravail et la productivité"
    # `discipline` est déclarée dans la liste blanche des champs de base : elle est transmise.
    assert entree["discipline"] == "Gestion"


def test_champ_non_declare_jamais_transmis(settings):
    """On ne devine JAMAIS un champ : plusieurs agents refusent les champs inconnus."""
    dossier = {"sujet": "S", "contexte": {"champ_inconnu": "valeur"}}
    entree = handoff.construire_entree(settings, "e", "s", settings.par_numero[1], dossier, {})
    assert "champ_inconnu" not in entree


def test_upstream_recopie_la_sortie_reele(settings):
    etape = settings.par_numero[4]      # la problématique reçoit les étapes 1, 2 et 3
    sorties = {1: {"subject": "sujet réel"}, 2: {"problem": "problème réel"},
               3: {"corpus": {"documents": [1, 2, 3]}}}
    entree = handoff.construire_entree(settings, "e", "s", etape, {"sujet": "S"}, sorties)
    assert entree["upstream_subject"] == {"subject": "sujet réel"}
    assert entree["upstream_problem"] == {"problem": "problème réel"}
    # La structure IMBRIQUÉE est transmise intacte (c'est exactement le bug historique : 8
    # documents en sortie, 0 reçus).
    assert entree["upstream_literature"]["corpus"]["documents"] == [1, 2, 3]


def test_sortie_amont_manquante_empeche_le_lancement(settings):
    """Pas de sortie amont valide = on ÉCHOUE au lieu d'envoyer une entrée incomplète."""
    etape = settings.par_numero[4]
    with pytest.raises(OrchestratorError) as info:
        handoff.construire_entree(settings, "e", "s", etape, {"sujet": "S"}, {1: {"a": 1}})
    assert info.value.etat == EtatErreur.SORTIE_AMONT_MANQUANTE
    assert "étape" in info.value.message_etudiant.lower()


def test_dossier_inconnu_refuse(settings):
    with pytest.raises(OrchestratorError) as info:
        handoff.construire_entree(settings, "e", "s", settings.par_numero[1], None, {})
    assert info.value.etat == EtatErreur.DOSSIER_INCONNU
