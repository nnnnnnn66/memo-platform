"""Fluidité du parcours : ce que l'étudiant peut regarder, et ce qui reste interdit.

Demande du porteur : « le travail doit être fluide, l'étudiant doit avoir un service bien mais qui
ne le force pas avec des process trop stricts ». La ligne tenue ici :

- **REGARDER devant est libre** — un outil qui cache la suite force au lieu d'accompagner ;
- **PRODUIRE une étape à venir reste interdit** — c'est le garde-fou méthodologique du produit :
  on ne construit pas une question de recherche sur une problématique non validée.
"""

from orchestrateur_helpers import avancer
from orchestrator.core.config import charger
from orchestrator.pipeline import campaign


def _dossier(settings, etudiant="etu-flux", session="sess-flux"):
    campaign.creer_dossier(settings, etudiant, session, "Le télétravail et la productivité")
    return etudiant, session


def test_on_peut_regarder_une_etape_a_venir(settings):
    """Défaut corrigé : l'API répondait 409 « validez d'abord les précédentes ».

    Un étudiant qui veut simplement LIRE ce qui l'attend était bloqué — et le site, dont les douze
    étapes sont cliquables, aurait essuyé une erreur sur onze d'entre elles.
    """
    etudiant, session = _dossier(settings)

    detail = campaign.etape_detail(settings, etudiant, session, 5)

    assert detail["a_venir"] is True
    assert detail["ouverte"] is False
    assert detail["libelle"] == "Question de recherche"
    assert detail["position"] == 5
    assert detail["total_etapes"] == 12


def test_une_etape_a_venir_dit_ce_qu_elle_demandera(settings):
    """Sans cette phrase, une étape à venir n'est qu'une ligne grise : elle ne sert à rien."""
    etudiant, session = _dossier(settings)

    detail = campaign.etape_detail(settings, etudiant, session, 9)

    assert detail["resume"]
    assert detail["resume"] in charger().par_numero[9].resume


def test_une_etape_a_venir_ne_divulgue_aucune_production(settings):
    """Voir devant ne veut pas dire voir un résultat : il n'y en a pas, et ça doit se voir."""
    etudiant, session = _dossier(settings)

    detail = campaign.etape_detail(settings, etudiant, session, 7)

    assert detail["resultat"] == {}
    assert detail["inconnues"] == []
    assert detail["questions"] == []
    assert detail["verdict"] == ""


def test_la_position_est_comparee_en_position_pas_en_numero(settings, agent):
    """DÉFAUT RÉEL, introduit par le réordonnancement : la vérification globale porte le numéro 13
    et vient AVANT la conclusion qui porte le 11.

    Un test « numero > ouverte » se trompait donc dans les deux sens dès que ces deux étapes étaient
    en jeu. Ici, une fois les étapes 1 à 10 faites, l'étape ouverte est la vérification (13) : la
    conclusion (11) doit être annoncée comme À VENIR, pas comme disponible.
    """
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=10)
    assert campaign.etat(settings, etudiant, session)["etape_ouverte"] == 13

    conclusion = campaign.etape_detail(settings, etudiant, session, 11)
    verification = campaign.etape_detail(settings, etudiant, session, 13)
    passee = campaign.etape_detail(settings, etudiant, session, 10)

    assert conclusion["a_venir"] is True, "la conclusion vient APRÈS la vérification"
    assert verification["a_venir"] is False, "la vérification est l'étape ouverte"
    assert passee["a_venir"] is False, "l'étape 10 est déjà faite"


def test_une_etape_validee_n_est_jamais_annoncee_comme_a_venir(settings, agent):
    """Symétrique du défaut : après la vérification, celle-ci est DERRIÈRE l'étudiant."""
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=10)
    campaign.lancer_etape(settings, etudiant, session, transport=agent)
    campaign.decider(settings, etudiant, session, "accepted", transport=agent)
    assert campaign.etat(settings, etudiant, session)["etape_ouverte"] == 11

    verification = campaign.etape_detail(settings, etudiant, session, 13)

    assert verification["a_venir"] is False, "elle est derrière : elle ne peut plus être « à venir »"


def test_regarder_devant_ne_permet_pas_de_produire(settings, agent):
    """LE GARDE-FOU EST INTACT : consulter l'étape 5 ne fait pas avancer le dossier de l'étape 1."""
    etudiant, session = _dossier(settings)

    campaign.etape_detail(settings, etudiant, session, 5)
    etat = campaign.lancer_etape(settings, etudiant, session, transport=agent)

    assert etat["etape"] == 1, "c'est toujours l'étape ouverte qui est lancée — jamais une autre"
    assert len(agent.appels) == 1


def test_chaque_etape_dit_ce_qu_elle_demandera(settings):
    """Aucune étape ne doit être une page vide dans l'interface."""
    sans_phrase = [etape.numero for etape in settings.etapes if not etape.resume.strip()]

    assert sans_phrase == [], f"étapes sans phrase d'explication : {sans_phrase}"


def test_la_carte_publique_dit_ce_qui_attend_l_etudiant(settings):
    """Le site de l'étudiant reçoit tout ce qu'il faut pour afficher la route à venir."""
    carte = charger().etapes

    assert all(etape.resume for etape in carte)
    assert [etape.numero for etape in carte][-1] == 11     # la conclusion termine le parcours
