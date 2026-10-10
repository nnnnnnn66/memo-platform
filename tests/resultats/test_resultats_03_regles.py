"""Contrôles déterministes Q1–Q9 : chaque contrôle éprouvé dans les DEUX sens."""

from resultats_helpers import upstream_methodology

from research_results_analysis_agent.analysis import results_rules
from research_results_analysis_agent.schemas.analysis import (
    AnalysisPlan,
    ComputedResult,
    ComputedResults,
    ExamenHypothese,
    Resultat,
    StatutHypothese,
)
from research_results_analysis_agent.schemas.draft import DraftSection, ResultsDraft
from research_results_analysis_agent.schemas.input import ResultsAnalysisRequest
from research_results_analysis_agent.schemas.interpretation import Interpretation, Lecture
from research_results_analysis_agent.schemas.inventory import Inventory

COMPUTED = ComputedResults(resultats=[
    ComputedResult(id="R1", libelle="nombre de lignes analysées", valeur="6", effectif=6,
                   methode="effectif_total"),
    ComputedResult(id="R2", libelle="moyenne — productivite", valeur="6,17", effectif=6,
                   methode="moyenne", variable="productivite"),
])


def _request(**overrides):
    payload = {"student_id": "e", "subject_text": "Sujet",
               "upstream_methodology": upstream_methodology()}
    payload.update(overrides)
    return ResultsAnalysisRequest(**payload)


def _run(request=None, computed=None, plan=None, interpretation=None, draft=None, inventory=None):
    return results_rules.run_checks(
        request or _request(), computed or COMPUTED, plan or AnalysisPlan(),
        interpretation or Interpretation(), draft or ResultsDraft(), inventory or Inventory())


def test_q1_resultat_sans_reference_refuse():
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="", observation="Six réponses.")])
    assert any(v.startswith("Q1") for v in _run(plan=plan))


def test_q1_reference_inexistante_refusee():
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R99", observation="Six réponses.")])
    assert any(v.startswith("Q1") for v in _run(plan=plan))


def test_q1_resultat_reference_accepte():
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R1", observation="Six réponses.")],
                        analyses_realisees=["effectif"])
    assert not any(v.startswith("Q1") for v in _run(plan=plan))


def test_q2_chiffre_invente_refuse():
    """Le cœur anti-invention : « 9,4 » n'a été calculé nulle part."""
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R1",
                                            observation="La moyenne atteint 9,4 sur l'échelle.")],
                        analyses_realisees=["moyenne"])
    violations = _run(plan=plan)
    assert any(v.startswith("Q2") and "9,4" in v for v in violations)


def test_q2_chiffre_calcule_accepte():
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R2",
                                            observation="La moyenne calculée est de 6,17.")],
                        analyses_realisees=["moyenne"])
    assert not any(v.startswith("Q2") for v in _run(plan=plan))


def test_q3_hypothese_soutenue_sans_resultat_refusee():
    plan = AnalysisPlan(hypotheses=[ExamenHypothese(hypothese="H1", statut=StatutHypothese.soutenue,
                                                    justification="cohérente", resultats=[])],
                        analyses_realisees=["descriptif"])
    assert any(v.startswith("Q3") for v in _run(plan=plan))


def test_q3_non_examinable_accepte():
    """« non examinable » est une réponse JUSTE quand les données ne permettent pas l'examen."""
    plan = AnalysisPlan(hypotheses=[ExamenHypothese(hypothese="H1",
                                                    statut=StatutHypothese.non_examinable,
                                                    justification="effectif trop faible",
                                                    resultats=[])],
                        analyses_realisees=["descriptif"])
    assert not any(v.startswith("Q3") for v in _run(plan=plan))


def test_q4_hypothese_confirmee_refusee():
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R1", observation="Six réponses.")],
                        analyses_realisees=["descriptif"])
    draft = ResultsDraft(sections=[DraftSection(titre="Résultats",
                                                contenu="L'hypothèse H1 est confirmée par l'analyse.",
                                                resultats=["R1"])])
    assert any(v.startswith("Q4") for v in _run(plan=plan, draft=draft))


def test_q5_causalite_sans_dispositif_refusee():
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R1",
                                            observation="Le télétravail provoque une hausse de la "
                                                        "productivité.")],
                        analyses_realisees=["descriptif"])
    assert any(v.startswith("Q5") for v in _run(plan=plan))


def test_q5_causalite_ecartee_non_refusee():
    """Une phrase qui ÉCARTE la causalité ne doit pas déclencher le contrôle (leçon M4/P7)."""
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R1",
                                            observation="Aucune causalité ne peut être établie avec "
                                                        "ce dispositif descriptif.")],
                        analyses_realisees=["descriptif"])
    assert not any(v.startswith("Q5") for v in _run(plan=plan))


def test_q6_lecture_sans_observation_refusee():
    interpretation = Interpretation(lectures=[Lecture(id_resultat="R1", observation="",
                                                      interpretation="Les valeurs suggèrent une "
                                                                     "relation.")])
    violations = _run(interpretation=interpretation)
    assert any(v.startswith("Q6") for v in violations)


def test_q7_manquants_non_declares_refuses():
    request = _request(datasets=[{"nom": "jeu", "format": "csv",
                                  "contenu": "a,b\n1,\n2,3\n"}])
    inventory = Inventory(provenance="test", datasets_resumes=["jeu"], manquants=[])
    violations = _run(request=request, inventory=inventory)
    assert any(v.startswith("Q7") for v in violations)


def test_q8_citation_inventee_refusee():
    interpretation = Interpretation(lectures=[Lecture(
        id_resultat="R1", observation="Six réponses.", 
        interpretation="Un répondant déclare « je travaille mieux chez moi le matin ».")])
    assert any(v.startswith("Q8") for v in _run(interpretation=interpretation))


def test_q9_conclusion_generale_refusee():
    draft = ResultsDraft(sections=[DraftSection(
        titre="Synthèse", contenu="En conclusion, notre étude démontre que le télétravail est "
                                  "bénéfique.", resultats=["R1"])])
    assert any(v.startswith("Q9") for v in _run(draft=draft))


def test_production_conforme_sans_violation():
    plan = AnalysisPlan(resultats=[Resultat(id_resultat="R1",
                                            observation="Six réponses ont été analysées.",
                                            objectif="Décrire l'échantillon.")],
                        analyses_realisees=["effectif et fréquences"],
                        hypotheses=[ExamenHypothese(hypothese="H1",
                                                    statut=StatutHypothese.non_examinable,
                                                    justification="effectif trop faible")])
    interpretation = Interpretation(lectures=[Lecture(
        id_resultat="R1", observation="Six réponses ont été analysées.",
        interpretation="Le corpus reste trop restreint pour une analyse relationnelle.")],
        limites_analyse=["Effectif faible"])
    assert _run(plan=plan, interpretation=interpretation) == []
