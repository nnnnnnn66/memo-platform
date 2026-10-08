"""Neutralité et forme de la question : contrôles DÉTERMINISTES (SPEC §10.C, §10.D)."""

from research_question_agent.analysis import question_rules as qr
from research_question_agent.pipeline import formulation_checks


def test_question_neutre_acceptee():
    q = "Dans quelle mesure le télétravail influence-t-il la productivité des développeurs ?"
    assert formulation_checks.check_question_text(q, "contexte sans prémisse") == []
    assert not qr.is_double_question(q)
    assert not qr.is_too_broad(q)


def test_presuppose_non_etabli_detecte():
    q = "Pourquoi cette politique est-elle inefficace ?"
    violations = formulation_checks.check_question_text(q, "contexte neutre sans jugement")
    assert any(v.startswith("F2") for v in violations)
    assert "inefficace" in qr.detect_premises(q)


def test_presuppose_etabli_par_les_entrees_accepte():
    q = "Pourquoi cette politique est-elle inefficace ?"
    # L'inefficacité est explicitement établie dans le contexte fourni par l'étudiant.
    context = "Le rapport officiel établit que la politique est inefficace depuis 2019."
    violations = formulation_checks.check_question_text(q, context)
    assert not any(v.startswith("F2") for v in violations)


def test_question_double_detectee():
    q = "Pourquoi le télétravail progresse-t-il et comment affecte-t-il la productivité ?"
    assert qr.is_double_question(q)
    assert any(v.startswith("F3") for v in formulation_checks.check_question_text(q, "x"))


def test_dans_quelle_mesure_n_est_pas_double():
    assert not qr.is_double_question("Dans quelle mesure X influence-t-il Y ?")


def test_question_trop_large_detectee():
    assert qr.is_too_broad("Quel est l'impact ?")
    assert any(v.startswith("F4")
               for v in formulation_checks.check_question_text("Quel est l'impact ?", "x"))


def test_delimitation_sans_source_signalee():
    scope = qr.__dict__  # placeholder pour prouver l'API via unsourced_boundaries
    from research_question_agent.schemas.question import ScopeAndBoundaries
    boundaries = ScopeAndBoundaries(geo="Abidjan", temps="", population="")
    added = qr.unsourced_boundaries(boundaries, "sujet sans mention géographique")
    assert "geo" in added


def test_delimitation_presente_dans_les_entrees_acceptee():
    from research_question_agent.schemas.question import ScopeAndBoundaries
    boundaries = ScopeAndBoundaries(geo="Abidjan", temps="2020-2024", population="")
    added = qr.unsourced_boundaries(boundaries, "étude menée à Abidjan entre 2020-2024")
    assert added == {}


def test_delimitation_composee_issue_de_champs_distincts_acceptee():
    """« Côte d'Ivoire, Abidjan » n'est pas inventé si le pays ET la ville sont fournis.

    Bug du test réel : les entrées étudiantes contiennent le pays dans un champ et la ville dans un
    autre ; exiger la chaîne entière comme bloc contigu signalait à tort (F5) une délimitation
    pourtant fournie → la campagne échouait avant le vérificateur.
    """
    from research_question_agent.schemas.question import ScopeAndBoundaries

    provided = "Pays : Côte d'Ivoire\nZone géographique : Abidjan\nPériode : 2020-2024"
    boundaries = ScopeAndBoundaries(geo="Côte d'Ivoire, Abidjan", temps="2020 - 2024",
                                    population="développeurs")
    added = qr.unsourced_boundaries(boundaries, provided)
    assert "geo" not in added        # pays + ville fournis séparément
    assert "temps" not in added      # années fournies
    assert "population" in added     # population jamais fournie : signalée


def test_delimitation_composee_inventee_signalee():
    from research_question_agent.schemas.question import ScopeAndBoundaries

    boundaries = ScopeAndBoundaries(geo="Abidjan, Dakar", temps="", population="")
    added = qr.unsourced_boundaries(boundaries, "Pays : Côte d'Ivoire\nZone géographique : Abidjan")
    assert "geo" in added            # Dakar n'est nulle part : on ne l'accepte pas
