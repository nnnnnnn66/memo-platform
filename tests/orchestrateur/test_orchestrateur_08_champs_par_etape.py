"""Le pont ne doit envoyer à chaque agent QUE les champs que son schéma accepte.

Défaut réel n°1 (trouvé en test simulé) : l'agent de l'étape 1 refuse les champs inconnus
(`extra="forbid"`) → **HTTP 422 « Extra inputs are not permitted »**.

Défaut réel n°2 (trouvé au PREMIER parcours de bout en bout, invisible jusqu'alors) : seules les
étapes déclarant une liste étaient protégées ; toutes les autres recevaient la liste globale, donc
`geographical_scope` et `period` — que l'agent de l'étape 2 refuse. Le parcours s'arrêtait à la
deuxième étape.

Défaut réel n°3, découvert en corrigeant le n°2 : **les agents n'ont pas choisi les mêmes noms pour
la même information** — `period` chez les uns, `study_period` chez les autres ; `geographical_scope`
ici, `geographical_area` là. Une liste de noms ne peut pas traduire, d'où la table de correspondance.
"""

import json

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


def test_chaque_etape_declare_les_champs_que_son_agent_accepte(settings):
    """Aucune étape ne doit retomber sur la liste globale : c'est ce qui a cassé l'étape 2."""
    sans_table = [etape.numero for etape in settings.etapes if not etape.champs]

    assert sans_table == [], f"étapes sans table de correspondance : {sans_table}"


def test_aucune_etape_ne_permet_a_son_agent_de_refuser_un_champ(settings):
    """LE test qui aurait attrapé le 422 : tout champ envoyé est déclaré par l'étape.

    Un champ expédié à un agent qui ne le déclare pas le fait échouer — et c'est invisible en test
    simulé, puisque l'agent simulé accepte tout.
    """
    for etape in settings.etapes:
        _, entree = _entree(settings, etape.numero)
        autorises = (set(etape.champs.values()) | {"student_id", "session_id"}
                     | set(etape.upstream))
        if etape.contexte_libre:
            autorises.add(etape.contexte_libre)

        inconnus = set(entree) - autorises
        assert not inconnus, (f"étape {etape.numero} envoie à son agent des champs qu'il n'a pas "
                              f"déclarés : {sorted(inconnus)}")


def test_aucun_champ_de_l_etudiant_n_est_perdu(settings):
    """Aucune information fournie par l'étudiant ne disparaît : elle change de champ."""
    for etape in settings.etapes:
        _, entree = _entree(settings, etape.numero)
        envoye = json.dumps(entree, ensure_ascii=False)

        assert "Abidjan" in envoye, f"étape {etape.numero} : la zone géographique a disparu"
        assert "2020-2024" in envoye, f"étape {etape.numero} : la période a disparu"


def test_les_champs_acceptes_sont_transmis_sous_leur_nom(settings):
    _, entree = _entree(settings, 1)

    assert entree["subject_text"] == DOSSIER["sujet"]
    assert entree["discipline"] == "Sciences de gestion"
    assert entree["country"] == "Côte d'Ivoire"
    assert entree["student_id"] == "etudiant-1"
    assert entree["session_id"] == "session-1"


def test_les_champs_non_acceptes_sont_recopies_avec_leur_intitule(settings):
    """L'étape 1 refuse la zone, la période et le problème observé : ils partent en contexte."""
    _, entree = _entree(settings, 1)

    contexte = entree["student_context"]
    assert "Abidjan" in contexte and "2020-2024" in contexte
    assert "Les entreprises constatent des effets contrastés." in contexte
    # Intitulés lisibles, jamais des noms techniques
    assert "zone géographique" in contexte
    assert "période étudiée" in contexte
    assert "geographical_scope" not in contexte


def test_un_nom_divergent_est_traduit(settings):
    """L'agent de l'étape 9 attend `geographical_area` et `study_period`, pas nos noms à nous."""
    _, entree = _entree(settings, 9)

    assert entree["geographical_area"] == "Abidjan"
    assert entree["study_period"] == "2020-2024"
    assert "geographical_scope" not in entree, "notre nom ferait échouer son schéma"
    assert "period" not in entree


def test_une_etape_qui_accepte_tout_ne_recopie_rien(settings):
    """L'étape 3 accepte la zone et la période sous nos noms : aucun contexte de recopie."""
    etape, entree = _entree(settings, 3)

    assert entree["geographical_scope"] == "Abidjan"
    assert entree["period"] == "2020-2024"
    assert etape.contexte_libre not in entree


def test_une_etape_sans_champ_de_contexte_ne_recoit_rien_en_trop(settings):
    """Cas limite : si un agent n'offre aucun champ de contexte libre, on n'invente pas de champ."""
    import dataclasses

    etape = dataclasses.replace(settings.par_numero[2], contexte_libre="")
    sorties = {source: {"sortie": "réelle"} for source in set(etape.upstream.values())}
    entree = handoff.construire_entree(settings, "etudiant-1", "session-1", etape, DOSSIER, sorties)

    assert "subject_context" not in entree
    assert "geographical_scope" not in entree
    assert "period" not in entree
