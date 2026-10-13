"""Mode AUTONOME : la plateforme avance sans attendre une validation (consigne du porteur).

« je ne veux pas qu'il attende ma validation, ils seront en ligne, donc ils doivent être
indépendants […] qu'ils soient rapides et autonomes. »

Ce que ces tests protègent :
- une étape produite ET VÉRIFIÉE ouvre la suivante toute seule ;
- une production NON vérifiée n'est JAMAIS validée automatiquement — on s'arrête et on le dit,
  parce que les étapes suivantes la refuseraient de toute façon ;
- le mode humain reste disponible et inchangé.
"""

import dataclasses

from orchestrator.pipeline import campaign


def _autonome(settings):
    return dataclasses.replace(settings, validation_automatique=True)


def test_une_etape_verifiee_ouvre_la_suivante_sans_decision(settings, agent):
    autonome = _autonome(settings)
    campaign.creer_dossier(autonome, "etu-auto", "s1", "Un sujet")

    reponse = campaign.lancer_etape(autonome, "etu-auto", "s1", transport=agent)

    assert reponse["verdict"] == "verified"
    assert reponse["decision_automatique"] is True, "personne ne doit avoir à cliquer"
    assert reponse["etape_suivante"] == 2
    # L'étape est bel et bien franchie, et le dossier a avancé.
    etat = campaign.etat(autonome, "etu-auto", "s1")
    assert etat["etape_ouverte"] == 2


def test_le_parcours_entier_s_enchainetout_seul(settings, agent):
    """Douze étapes d'affilée, sans une seule décision humaine."""
    autonome = _autonome(settings)
    campaign.creer_dossier(autonome, "etu-auto2", "s2", "Un sujet")

    for _ in range(12):
        reponse = campaign.lancer_etape(autonome, "etu-auto2", "s2", transport=agent)
        assert reponse["decision_automatique"] is True, reponse
        if reponse["etape_suivante"] is None:
            break

    etat = campaign.etat(autonome, "etu-auto2", "s2")
    validees = [ligne for ligne in etat["avancement"] if ligne["statut"] == "validee"]
    assert len(validees) == len(autonome.etapes), "toutes les étapes doivent être franchies"


def test_une_production_non_verifiee_n_est_jamais_validee_seule(settings, agent):
    """Le mode autonome ne dispense PAS de la vérification : c'est elle qui remplace la décision.

    Une production non vérifiée ferait échouer l'étape suivante (elle refuse de s'appuyer dessus) :
    valider automatiquement ferait avancer sur du vide. On s'arrête donc, et l'état le dit.
    """
    autonome = _autonome(settings)
    agent.verdict = "pending"
    campaign.creer_dossier(autonome, "etu-auto3", "s3", "Un sujet")

    reponse = campaign.lancer_etape(autonome, "etu-auto3", "s3", transport=agent)

    assert reponse["decision_automatique"] is False
    assert reponse["etape_suivante"] is None
    assert campaign.etat(autonome, "etu-auto3", "s3")["etape_ouverte"] == 1, "rien n'a avancé"


def test_le_mode_humain_reste_inchange(settings, agent):
    """Le réglage par défaut ne bouge pas : sans la consigne, une étape attend une décision."""
    assert settings.validation_automatique is False
    campaign.creer_dossier(settings, "etu-humain", "s4", "Un sujet")

    reponse = campaign.lancer_etape(settings, "etu-humain", "s4", transport=agent)

    assert reponse["decision_automatique"] is False
    assert campaign.etat(settings, "etu-humain", "s4")["etape_ouverte"] == 1

    campaign.decider(settings, "etu-humain", "s4", "accepted", transport=agent)
    assert campaign.etat(settings, "etu-humain", "s4")["etape_ouverte"] == 2


def test_la_decision_humaine_reste_possible_en_mode_autonome(settings, agent):
    """Autonome ne veut pas dire « sans recours » : l'étudiant peut toujours demander une révision."""
    autonome = _autonome(settings)
    campagne = dataclasses.replace(autonome, validation_automatique=False)
    campaign.creer_dossier(campagne, "etu-auto4", "s5", "Un sujet")
    campaign.lancer_etape(campagne, "etu-auto4", "s5", transport=agent)

    refus = campaign.decider(campagne, "etu-auto4", "s5", "refused", "Le sujet doit être précisé")

    assert refus["decision"] == "refused"
    assert campaign.etat(campagne, "etu-auto4", "s5")["etape_ouverte"] == 1, \
        "une révision redonne la main sur la même étape"
