"""Matrice d'alignement théorique (SPEC §4.4A) : détection et cohérence."""

from literature_review_agent.diagnosis import matrix


def test_matrice_complete():
    assert len(matrix.MATRIX) == 8
    assert matrix.BY_ID["test_hypothesis"].approach == "quantitative"
    assert matrix.BY_ID["explore_experiences"].reasoning_logic == "inductive"


def test_detection_des_indicateurs():
    rows = matrix.detect_rows("Quel est l'impact du télétravail sur la productivité ?")
    assert [row.id for row in rows] == ["test_hypothesis"]

    rows = matrix.detect_rows("Quel est le vécu des développeurs en télétravail ?")
    assert "explore_experiences" in [row.id for row in rows]

    rows = matrix.detect_rows("Comment fonctionne ce dispositif encore peu étudié ?")
    assert "explore_phenomenon" in [row.id for row in rows]

    rows = matrix.detect_rows("Dans quelle mesure la théorie de X s'applique-t-elle ici ?")
    assert "verify_theory" in [row.id for row in rows]


def test_coherence_ligne_respectee():
    assert matrix.row_coherence_issues("test_hypothesis", "hypothetico_deductive", "explanatory",
                                       "quantitative", ["régression"]) == []


def test_incoherence_signalee():
    issues = matrix.row_coherence_issues("explore_experiences", "hypothetico_deductive",
                                         "explanatory", "quantitative", ["régression"])
    assert any("logique" in issue for issue in issues)
    assert any("approche" in issue for issue in issues)


def test_combinaison_mixte_toleree():
    assert matrix.row_coherence_issues("test_hypothesis", "mixed", "mixed", "mixed_methods",
                                       ["entretiens", "questionnaire"]) == []


def test_ligne_inconnue_rejetee():
    issues = matrix.row_coherence_issues("ligne_bidon", "inductive", "exploratory", "qualitative",
                                         ["entretiens"])
    assert issues and "inconnue" in issues[0]


def test_alias_normalises():
    assert matrix.normalize_logic("Hypothético-déductif") == "hypothetico_deductive"
    assert matrix.normalize_research_type("Corrélationnelle") == "correlational"
