"""REPRENDRE UNE ÉTAPE DÉJÀ FRANCHIE — le manque comblé.

Contexte : une étape validée était DÉFINITIVE. Pour y revenir, il fallait intervenir directement
dans la base SQLite (fait lors d'un parcours réel). Or un mémoire est itératif : l'étudiant reçoit
de nouvelles données, ou veut corriger. Une plateforme en ligne doit le permettre.

Ce que ces tests protègent — les règles à NE PAS casser :
1. on peut reprendre une étape franchie, et elle redevient l'étape OUVERTE ;
2. on ne peut pas « reprendre » une étape JAMAIS atteinte (ni une étape hors parcours) ;
3. le parcours reste COHÉRENT : les étapes aval qui s'appuyaient sur la version antérieure cessent
   d'être `validee` et sont dites « à revoir », avec la raison (`repose_sur`) ;
4. « non vérifiée ⇒ on n'avance pas » reste VRAI après une reprise : rejouer une étape n'ouvre
   rien si son nouveau passage n'est pas vérifié ;
5. les décisions déjà prises restent TRAÇABLES (journal `reprises`).
"""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from orchestrator.core.errors import EtatErreur, OrchestratorError
from orchestrator.main import app
from orchestrator.pipeline import campaign
from orchestrator.storage import state

from orchestrateur_helpers import avancer


def _dossier(settings, etudiant="etu-reprise", session="sess-reprise"):
    campaign.creer_dossier(settings, etudiant, session, "Le télétravail et la productivité")
    return etudiant, session


def _autonome(settings):
    return dataclasses.replace(settings, validation_automatique=True)


# ---------------------------------------------------------------- 1. reprendre une étape franchie

def test_reprendre_une_etape_franchie_la_rouvre(settings, agent):
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    assert campaign.etat(settings, etudiant, session)["etape_ouverte"] == 6

    resultat = campaign.reprendre(settings, etudiant, session, 3)

    assert resultat["reprise"] is True
    assert resultat["etape"] == 3
    assert resultat["statut"] == state.STATUT_A_FAIRE
    assert resultat["etape_ouverte"] == 3, "l'étape reprise redevient l'étape ouverte"
    assert resultat["ancien_statut"] == state.STATUT_VALIDEE
    assert resultat["ancienne_decision"] == "accepted"
    assert campaign.etat(settings, etudiant, session)["etape_ouverte"] == 3


def test_la_reprise_ne_consomme_pas_de_quota(settings, agent):
    """Rouvrir une étape ne fait AUCUN appel d'agent : ce ne doit pas coûter au portefeuille."""
    from orchestrator.pipeline import quota

    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    avant = quota.restant(settings.state_db, etudiant, settings.analyses_par_jour)

    campagne = campaign.reprendre(settings, etudiant, session, 3)

    assert quota.restant(settings.state_db, etudiant, settings.analyses_par_jour) == avant
    assert campagne["reprise"] is True


# ------------------------------------------------- 2. refus de reprendre ce qui n'est pas franchi

def test_refus_de_reprendre_une_etape_jamais_atteinte(settings):
    """Aucune production n'existe : il n'y a rien à reprendre. On refuse, en le disant."""
    etudiant, session = _dossier(settings)

    with pytest.raises(OrchestratorError) as info:
        campaign.reprendre(settings, etudiant, session, 5)

    assert info.value.etat == EtatErreur.ETAPE_NON_AUTORISEE
    assert "franchi" in info.value.message_etudiant
    assert campaign.etat(settings, etudiant, session)["etape_ouverte"] == 1, "rien n'a bougé"


def test_refus_de_reprendre_la_premiere_etape_d_un_dossier_neuf(settings):
    etudiant, session = _dossier(settings)
    with pytest.raises(OrchestratorError) as info:
        campaign.reprendre(settings, etudiant, session, 1)
    assert info.value.etat == EtatErreur.ETAPE_NON_AUTORISEE


def test_refus_de_reprendre_une_etape_encore_ouverte(settings, agent):
    """Une étape PROPOSÉE n'est pas franchie : la relancer est déjà possible."""
    etudiant, session = _dossier(settings)
    campaign.lancer_etape(settings, etudiant, session, transport=agent)

    with pytest.raises(OrchestratorError) as info:
        campaign.reprendre(settings, etudiant, session, 1)

    assert info.value.etat == EtatErreur.ETAPE_NON_AUTORISEE
    assert campaign.etat(settings, etudiant, session)["statut"] == state.STATUT_PROPOSEE


def test_refus_de_reprendre_une_etape_hors_parcours(settings):
    etudiant, session = _dossier(settings)
    with pytest.raises(OrchestratorError) as info:
        campaign.reprendre(settings, etudiant, session, 12)   # 12 est RÉSERVÉE : hors parcours
    assert info.value.etat == EtatErreur.ETAPE_INCONNUE


def test_refus_de_reprendre_sur_un_dossier_inconnu(settings):
    with pytest.raises(OrchestratorError) as info:
        campaign.reprendre(settings, "personne", "inconnu", 1)
    assert info.value.etat == EtatErreur.DOSSIER_INCONNU


# ------------------------------------------------------- 3. le parcours reste cohérent après reprise

def test_les_etapes_aval_cessent_d_etre_validees(settings, agent):
    """On ne peut pas savoir SI la nouvelle production différera : les étapes aval ne doivent donc
    pas rester « validées » en silence. Leur contenu est CONSERVÉ, leur statut change."""
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    production_aval = state.sortie_validee(settings.state_db, etudiant, session, 4)
    assert production_aval is not None

    resultat = campaign.reprendre(settings, etudiant, session, 3)

    assert [item["numero"] for item in resultat["etapes_aval_a_revoir"]] == [4, 5]
    assert state.statut(settings.state_db, etudiant, session, 4)["statut"] == state.STATUT_A_REVISER
    assert state.statut(settings.state_db, etudiant, session, 5)["statut"] == state.STATUT_A_REVISER
    # La production reste lisible (pour l'étudiant), mais elle n'est PLUS transmissible.
    assert state.sortie_proposee(settings.state_db, etudiant, session, 4) == production_aval
    assert state.sortie_validee(settings.state_db, etudiant, session, 4) is None


def test_une_etape_aval_dit_sur_quoi_elle_repose(settings, agent):
    """« À revoir » ne suffit pas : l'étudiant doit lire POURQUOI."""
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    campaign.reprendre(settings, etudiant, session, 3)

    detail = campaign.etape_detail(settings, etudiant, session, 4)

    assert detail["statut"] == state.STATUT_A_REVISER
    assert detail["repose_sur"] == {"numero": 3, "libelle": "Revue de littérature",
                                    "statut": state.STATUT_A_FAIRE}
    # L'étape reprise, elle, ne « repose » sur rien : elle est la source.
    assert campaign.etape_detail(settings, etudiant, session, 3)["repose_sur"] is None


def test_la_reprise_reouvre_l_etape_et_pas_une_autre(settings, agent):
    """Le garde-fou de production est intact : c'est l'étape reprise qui est lancée."""
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    campaign.reprendre(settings, etudiant, session, 3)

    lancee = campaign.lancer_etape(settings, etudiant, session, transport=agent)

    assert lancee["etape"] == 3, "jamais l'étape 6 ni une étape aval"
    assert "8030" in agent.appels[-1][0], "l'agent appelé est bien celui de l'étape 3"


def test_le_parcours_se_referme_dans_l_ordre_apres_reprise(settings, agent):
    """Reprise de 3 → on rejoue 3, puis 4 et 5 : la cohérence est rétablie, dans l'ORDRE."""
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    campaign.reprendre(settings, etudiant, session, 3)

    avancer(settings, etudiant, session, agent, nombre=3)      # rejoue 3, 4, 5

    etat_final = campaign.etat(settings, etudiant, session)
    assert etat_final["etape_ouverte"] == 6
    statuts = {ligne["numero"]: ligne["statut"] for ligne in etat_final["avancement"]}
    assert statuts[3] == state.STATUT_VALIDEE
    assert statuts[4] == state.STATUT_VALIDEE
    assert statuts[5] == state.STATUT_VALIDEE
    # Les étapes aval rejouées ne « reposent » plus sur une version antérieure.
    assert campaign.etape_detail(settings, etudiant, session, 4)["repose_sur"] is None


def test_apres_reprise_le_pont_transmet_la_NOUVELLE_production(settings, agent):
    """Le contrat `upstream_*` doit rester honnête : la nouvelle sortie remplace l'ancienne."""
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    ancienne = agent.resultat
    campaign.reprendre(settings, etudiant, session, 3)

    nouvelle = {"status": "awaiting_human_validation", "proposition": "revue REFONDUE"}
    agent.resultat = nouvelle
    campaign.lancer_etape(settings, etudiant, session, transport=agent)     # rejoue l'étape 3
    campaign.decider(settings, etudiant, session, "accepted", transport=agent)
    campaign.lancer_etape(settings, etudiant, session, transport=agent)     # étape 4

    entree4 = agent.derniere_entree
    assert entree4["upstream_literature"] == nouvelle
    assert entree4["upstream_literature"] != ancienne


# ------------------------------------- 4. « non vérifiée ⇒ on n'avance pas » reste vrai après reprise

def test_une_reprise_non_verifiee_n_ouvre_rien(settings, agent):
    """Mode autonome : une reprise rejouée SANS verdict `verified` ne franchit RIEN."""
    autonome = _autonome(settings)
    campaign.creer_dossier(autonome, "etu-rep-auto", "s1", "Un sujet")
    for _ in range(5):
        campaign.lancer_etape(autonome, "etu-rep-auto", "s1", transport=agent)
    assert campaign.etat(autonome, "etu-rep-auto", "s1")["etape_ouverte"] == 6

    campaign.reprendre(autonome, "etu-rep-auto", "s1", 3)
    agent.verdict = "pending"                     # le nouveau passage n'est PAS vérifié
    reponse = campaign.lancer_etape(autonome, "etu-rep-auto", "s1", transport=agent)

    assert reponse["decision_automatique"] is False
    assert reponse["etape_suivante"] is None
    etat_dossier = campaign.etat(autonome, "etu-rep-auto", "s1")
    assert etat_dossier["etape_ouverte"] == 3, "rien n'a avancé"
    assert etat_dossier["verdict"] == "pending"
    # Les étapes aval restent « à revoir » — elles ne repassent pas « validées » par ricochet.
    assert state.statut(autonome.state_db, "etu-rep-auto", "s1", 4)["statut"] == state.STATUT_A_REVISER


def test_une_reprise_verifiee_en_autonome_rouvre_le_parcours(settings, agent):
    """Symétrique : une reprise VÉRIFIÉE referme l'étape et rouvre la suivante (l'étape aval)."""
    autonome = _autonome(settings)
    campaign.creer_dossier(autonome, "etu-rep-auto2", "s2", "Un sujet")
    for _ in range(5):
        campaign.lancer_etape(autonome, "etu-rep-auto2", "s2", transport=agent)

    campaign.reprendre(autonome, "etu-rep-auto2", "s2", 3)
    reponse = campaign.lancer_etape(autonome, "etu-rep-auto2", "s2", transport=agent)

    assert reponse["decision_automatique"] is True
    assert reponse["etape_suivante"] == 4
    assert state.statut(autonome.state_db, "etu-rep-auto2", "s2", 3)["statut"] == state.STATUT_VALIDEE
    assert campaign.etat(autonome, "etu-rep-auto2", "s2")["etape_ouverte"] == 4


# ------------------------------------------------------------- 5. les décisions restent traçables

def test_la_reprise_est_journalisee_avec_la_decision_anterieure(settings, agent):
    """`enregistrer_resultat` remet la décision à zéro : sans journal, elle disparaîtrait."""
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)

    campaign.reprendre(settings, etudiant, session, 3)

    journal = state.reprises(settings.state_db, etudiant, session, 3)
    assert len(journal) == 1
    entree = journal[0]
    assert entree["ancien_statut"] == state.STATUT_VALIDEE
    assert entree["ancienne_decision"] == "accepted"
    assert entree["ancien_verdict"] == "verified"
    assert entree["aval"] == [4, 5]

    # …et la reprise SURVIT au nouveau passage (nouveau résultat, décision écrasée).
    campaign.lancer_etape(settings, etudiant, session, transport=agent)
    campaign.decider(settings, etudiant, session, "accepted", transport=agent)
    assert len(state.reprises(settings.state_db, etudiant, session, 3)) == 1
    detail = campaign.etape_detail(settings, etudiant, session, 3)
    assert detail["reprises"] == 1
    assert detail["historique_reprises"][0]["ancienne_decision"] == "accepted"


def test_le_journal_des_reprises_est_expose_par_etape(settings, agent):
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)

    assert campaign.etape_detail(settings, etudiant, session, 5)["reprises"] == 0

    campaign.reprendre(settings, etudiant, session, 5)     # 5 est franchie : elle est rouverte
    assert campaign.etape_detail(settings, etudiant, session, 5)["reprises"] == 1

    campaign.reprendre(settings, etudiant, session, 3)     # 3 reste franchie, elle aussi rouverte
    assert campaign.etape_detail(settings, etudiant, session, 3)["reprises"] == 1
    avancement = {ligne["numero"]: ligne
                  for ligne in campaign.etat(settings, etudiant, session)["avancement"]}
    assert avancement[3]["reprises"] == 1
    assert avancement[5]["reprises"] == 1
    assert avancement[4]["reprises"] == 0


# ------------------------------------------------------------------------------- API HTTP interne

def _client(settings):
    app.state.settings = settings
    return TestClient(app)


def test_api_reprendre_renvoie_200(settings, agent):
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)

    reponse = _client(settings).post(f"/dossiers/{etudiant}/{session}/etapes/3/reprendre")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["reprise"] is True
    assert corps["etape_ouverte"] == 3
    assert [item["numero"] for item in corps["etapes_aval_a_revoir"]] == [4, 5]


def test_api_reprendre_une_etape_jamais_atteinte_renvoie_409(settings):
    etudiant, session = _dossier(settings)
    reponse = _client(settings).post(f"/dossiers/{etudiant}/{session}/etapes/4/reprendre")
    assert reponse.status_code == 409
    assert reponse.json()["detail"]["error"] == "ETAPE_NON_AUTORISEE"


def test_api_reprendre_une_etape_hors_parcours_renvoie_400(settings):
    etudiant, session = _dossier(settings)
    reponse = _client(settings).post(f"/dossiers/{etudiant}/{session}/etapes/12/reprendre")
    assert reponse.status_code == 400
    assert reponse.json()["detail"]["error"] == "ETAPE_INCONNUE"


def test_api_reprendre_sur_un_dossier_inconnu_renvoie_404(settings):
    reponse = _client(settings).post("/dossiers/personne/inconnu/etapes/1/reprendre")
    assert reponse.status_code == 404
    assert reponse.json()["detail"]["error"] == "DOSSIER_INCONNU"


def test_api_le_detail_dit_sur_quoi_l_etape_aval_repose(settings, agent):
    etudiant, session = _dossier(settings)
    avancer(settings, etudiant, session, agent, nombre=5)
    client = _client(settings)
    client.post(f"/dossiers/{etudiant}/{session}/etapes/3/reprendre")

    detail = client.get(f"/dossiers/{etudiant}/{session}/etape?n=4").json()

    assert detail["statut"] == "a_reviser"
    assert detail["repose_sur"]["numero"] == 3
    assert detail["reprises"] == 0
