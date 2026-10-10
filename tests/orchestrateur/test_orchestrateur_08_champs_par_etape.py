"""Le pont ne doit envoyer à chaque agent QUE les champs que son schéma accepte.

Défaut réel (trouvé en exécution, invisible en test simulé) : le site collecte « zone
géographique », « période » et « problème observé » à la création du dossier ; l'agent de l'étape 1
refuse tout champ inconnu (`extra="forbid"`) → **HTTP 422 « Extra inputs are not permitted »** et
l'étape échoue. Ces champs ne doivent être ni envoyés à un agent qui les refuse, ni perdus.
"""

from orchestrator.pipeline import handoff

DOSSIER = {
    "sujet": "Les effets du télétravail sur la productivité des salariés des PME d'Abidjan",
    "contexte": {
        "discipline": "Sciences de gestion",
        "country": "Côte d'Ivoire",
        "geographical_scope": "Abidjan",
        "period": "2020-2024",
        "research_problem": "Les entreprises constatent des effets contrastés.",
    },
}


def _entree(settings, numero):
    etape = settings.par_numero[numero]
    sorties = {source: {"sortie": "réelle"} for source in set(etape.upstream.values())}
    return etape, handoff.construire_entree(settings, "etudiant-1", "session-1", etape,
                                            DOSSIER, sorties)


def test_l_etape_1_declare_les_champs_que_son_agent_accepte(settings):
    etape = settings.par_numero[1]

    assert etape.champs, "l'étape 1 doit déclarer les champs acceptés par son agent"
    assert "subject_text" in etape.champs
    assert "student_context" in etape.champs


def test_aucun_champ_refuse_par_l_agent_n_est_envoye(settings):
    etape, entree = _entree(settings, 1)

    inconnus = set(entree) - set(etape.champs)

    assert not inconnus, f"champs que l'agent refuse : {sorted(inconnus)}"


def test_les_champs_acceptes_sont_transmis_tels_quels(settings):
    _, entree = _entree(settings, 1)

    assert entree["subject_text"] == DOSSIER["sujet"]
    assert entree["discipline"] == "Sciences de gestion"
    assert entree["country"] == "Côte d'Ivoire"
    assert entree["student_id"] == "etudiant-1"
    assert entree["session_id"] == "session-1"


def test_les_champs_non_acceptes_sont_recopies_et_non_perdus(settings):
    """Aucune information fournie par l'étudiant ne disparaît : elle change de champ."""
    _, entree = _entree(settings, 1)

    contexte = entree["student_context"]
    assert "Abidjan" in contexte
    assert "2020-2024" in contexte
    assert "Les entreprises constatent des effets contrastés." in contexte
    # Intitulés lisibles, pas des noms techniques
    assert "zone géographique" in contexte
    assert "période étudiée" in contexte
    assert "geographical_scope" not in contexte


def test_une_etape_sans_liste_propre_garde_le_comportement_global(settings):
    """Ne pas casser ce qui fonctionne sur les autres étapes : la liste globale s'applique."""
    etape, entree = _entree(settings, 4)

    assert not etape.champs
    assert entree["geographical_scope"] == "Abidjan"
    assert entree["period"] == "2020-2024"
    assert "student_context" not in entree
