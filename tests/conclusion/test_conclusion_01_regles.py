"""Contrôles déterministes K1–K9 : chacun éprouvé dans les DEUX sens."""

from conclusion_helpers import upstream_results

from research_conclusion_agent.analysis import conclusion_rules
from research_conclusion_agent.schemas.draft import ConclusionDraft, DraftSection, NiveauAffirmation
from research_conclusion_agent.schemas.input import ConclusionRequest
from research_conclusion_agent.schemas.plan import ConclusionPlan, PlanSection
from research_conclusion_agent.schemas.synthesis import (
    BilanHypothese,
    BilanObjectif,
    ReponseQuestion,
    StatutHypothese,
    StatutObjectif,
    Synthesis,
)


def _request(**overrides):
    payload = {"student_id": "e",
               "subject_text": "Sujet",
               "upstream_results": upstream_results(),
               "upstream_question": {"main_research_question": "Question ?",
                                     "verification_result": {"verified": True}},
               "upstream_methodology": {"protocol": {"type_recherche": "explicative"},
                                        "verification_result": {"verified": True}}}
    payload.update(overrides)
    return ConclusionRequest(**payload)


def _synthesis(**overrides):
    base = {"resultats_essentiels": ["R1"],
            "reponse_question": ReponseQuestion(question="Question ?", reponse="Réponse.",
                                                etayage=["R1"])}
    base.update(overrides)
    return Synthesis(**base)


def _run(request=None, synthesis=None, plan=None, draft=None):
    return conclusion_rules.run_checks(request or _request(), synthesis or _synthesis(),
                                       plan or ConclusionPlan(), draft or ConclusionDraft())


def test_k1_affirmation_sans_reference_refusee():
    """Aucune référence à un résultat de l'étape 10 : la conclusion n'est pas traçable."""
    draft = ConclusionDraft(sections=[DraftSection(titre="Résultats",
                                                   contenu="Le corpus a été décrit.",
                                                   justification="calculs", resultats=[])])
    synthesis = _synthesis(resultats_essentiels=[],
                           reponse_question=ReponseQuestion(question="Question ?",
                                                            reponse="Réponse.", etayage=[]))
    assert any(v.startswith("K1") for v in _run(synthesis=synthesis, draft=draft))


def test_k1_reference_inexistante_refusee():
    draft = ConclusionDraft(sections=[DraftSection(titre="Résultats", contenu="Le corpus est décrit.",
                                                   justification="calculs", resultats=["R99"])])
    assert any(v.startswith("K1") for v in _run(draft=draft))


def test_k1_reference_reelle_acceptee():
    draft = ConclusionDraft(sections=[DraftSection(titre="Résultats", contenu="Le corpus est décrit.",
                                                   justification="calculs", resultats=["R1"])])
    assert not any(v.startswith("K1") for v in _run(draft=draft))


def test_k2_chiffre_hors_resultats_refuse():
    """Anti-invention : « 8,4 » n'a jamais été calculé à l'étape 10."""
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Résultats", contenu="La productivité moyenne s'établit à 8,4 sur l'échelle.",
        justification="calculs", resultats=["R1"])])
    violations = _run(draft=draft)
    assert any(v.startswith("K2") and "8,4" in v for v in violations)


def test_k2_chiffre_issu_des_resultats_accepte():
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Résultats", contenu="Le corpus analysé rassemble vingt réponses exploitables.",
        justification="calculs", resultats=["R1"])])
    assert not any(v.startswith("K2") for v in _run(draft=draft))


def test_k3_statut_contredisant_l_etape_10_refuse():
    """L'étape 10 a jugé l'hypothèse non examinable : elle ne peut pas devenir « soutenue » ici."""
    synthesis = _synthesis(bilan_hypotheses=[BilanHypothese(
        hypothese="L'intensité du télétravail est associée à la productivité déclarée.",
        statut=StatutHypothese.soutenue, justification="les chiffres vont dans ce sens",
        resultats=["R1"])])
    assert any(v.startswith("K3") for v in _run(synthesis=synthesis))


def test_k3_statut_conforme_accepte():
    synthesis = _synthesis(bilan_hypotheses=[BilanHypothese(
        hypothese="L'intensité du télétravail est associée à la productivité déclarée.",
        statut=StatutHypothese.non_examinable, justification="effectif trop faible")])
    assert not any(v.startswith("K3") for v in _run(synthesis=synthesis))


def test_k4_causalite_sans_dispositif_refusee():
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Réponse", contenu="Le télétravail provoque une hausse de la productivité déclarée.",
        justification="calculs", resultats=["R1"])])
    assert any(v.startswith("K4") for v in _run(draft=draft))


def test_k4_causalite_ecartee_non_refusee():
    """Une phrase qui ÉCARTE la causalité ne doit pas déclencher le contrôle (leçon M4/P7)."""
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Réponse", contenu="Ce dispositif ne permet pas d'établir une causalité : aucune "
                                 "lecture causale n'est proposée.",
        justification="dispositif descriptif", resultats=["R1"])])
    assert not any(v.startswith("K4") for v in _run(draft=draft))


def test_k5_hypothese_confirmee_refusee():
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Bilan", contenu="L'hypothèse H1 est confirmée par les résultats.",
        justification="calculs", resultats=["R1"])])
    assert any(v.startswith("K5") for v in _run(draft=draft))


def test_k6_reference_absente_du_dossier_refusee():
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Discussion", contenu="Ce résultat rejoint (Durand, 2019).",
        justification="comparaison", resultats=["R1"])])
    assert any(v.startswith("K6") for v in _run(draft=draft))


def test_k7_perspective_dans_un_constat_refusee():
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Constats", contenu="À l'avenir, il serait utile d'étendre le recueil.",
        justification="piste", niveau=NiveauAffirmation.constat, resultats=["R1"])])
    assert any(v.startswith("K7") for v in _run(draft=draft))


def test_k7_perspective_declaree_acceptee():
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Perspectives", contenu="À l'avenir, il serait utile d'étendre le recueil.",
        justification="piste issue des limites", niveau=NiveauAffirmation.perspective,
        resultats=["R1"])])
    assert not any(v.startswith("K7") for v in _run(draft=draft))


def test_k8_conclusion_redigee_sans_resultats_refusee():
    request = _request(upstream_results=upstream_results(plan_seulement=True))
    synthesis = _synthesis(plan_seulement=True, resultats_essentiels=[],
                           reponse_question=ReponseQuestion(question="Question ?"))
    draft = ConclusionDraft(sections=[DraftSection(titre="Conclusion", contenu="En somme…",
                                                   justification="x")])
    assert any(v.startswith("K8") for v in _run(request=request, synthesis=synthesis, draft=draft))


def test_k8_plan_seul_accepte():
    request = _request(upstream_results=upstream_results(plan_seulement=True))
    synthesis = _synthesis(plan_seulement=True, resultats_essentiels=[],
                           reponse_question=ReponseQuestion(question="Question ?"),
                           elements_manquants=["résultats vérifiés"])
    assert _run(request=request, synthesis=synthesis) == []


def test_k9_resultat_inexistant_retenu_refuse():
    synthesis = _synthesis(resultats_essentiels=["R1", "R42"])
    assert any(v.startswith("K9") for v in _run(synthesis=synthesis))


def test_conclusion_conforme_sans_violation():
    synthesis = _synthesis(bilan_objectifs=[BilanObjectif(
        objectif="Décrire l'intensité du télétravail déclarée.", statut=StatutObjectif.atteint,
        resultats=["R1"])])
    plan = ConclusionPlan(sections=[PlanSection(titre="Synthèse", fonction="rappeler les constats")])
    draft = ConclusionDraft(sections=[DraftSection(
        titre="Synthèse", contenu="Le corpus analysé rassemble vingt réponses exploitables.",
        justification="calculs de l'étape 10", resultats=["R1"])])
    assert _run(synthesis=synthesis, plan=plan, draft=draft) == []
