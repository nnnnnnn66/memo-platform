"""Passation réelle : les quatre pièges qui ne se voient QUE sur les sorties produites.

Leçon de la chaîne 1 → 8 : les fixtures fabriquées à la main portent les clés ATTENDUES et non les
clés RÉELLEMENT produites, si bien que la suite reste verte pendant que la chaîne casse.
"""

from methodology_agent.schemas.input import MethodologyRequest
from methodology_agent.schemas.output import MethodologyOutput


def _request(**kw):
    return MethodologyRequest(student_id="e", discipline="Gestion", **kw)


# --- 1. la clé de vérification dépend de l'ÉMETTEUR -------------------------------------------
def test_cle_verification_result_acceptee_agents_5_a_8():
    payload = {"main_research_question": "Question ?",
               "verification_result": {"verified": True, "verifier_status": "verified"}}
    assert _request(upstream_question=payload).upstream_question.is_verified


def test_cle_validation_acceptee_agents_1_a_4():
    payload = {"identified_problem": {"statement": "Problème."},
               "validation": {"verified": True, "verifier_status": "verified"}}
    assert _request(upstream_problem=payload).upstream_problem.is_verified


def test_sortie_non_verifiee_toujours_refusee():
    payload = {"main_research_question": "Question ?",
               "verification_result": {"verified": False, "verifier_status": "pending"}}
    assert not _request(upstream_question=payload).upstream_question.is_verified


# --- 2. les champs lus sur l'amont existent RÉELLEMENT ----------------------------------------
def test_probleme_lu_dans_identified_problem_statement():
    payload = {"identified_problem": {"statement": "Le turnover s'aggrave depuis 2020."},
               "validation": {"verified": True, "verifier_status": "verified"}}
    assert _request(upstream_problem=payload).effective_problem() == \
        "Le turnover s'aggrave depuis 2020."


def test_problematique_lue_dans_problematique_note():
    payload = {"problematique_note": {"texte_complet": "Le télétravail ne résout pas…"},
               "validation": {"verified": True, "verifier_status": "verified"}}
    assert _request(upstream_problematic=payload).effective_problematic() == \
        "Le télétravail ne résout pas…"


def test_hypotheses_lues_dans_les_objets_de_l_agent_7():
    payload = {"research_hypotheses": [
        {"id": "H1", "formulation": "La coordination est liée à la productivité."},
        {"id": "H2", "formulation": "L'intensité module la productivité."}],
        "verification_result": {"verified": True, "verifier_status": "verified"}}
    assert _request(upstream_hypotheses=payload).effective_hypotheses() == [
        "La coordination est liée à la productivité.",
        "L'intensité module la productivité."]


def test_decision_hypotheses_not_required_detectee():
    payload = {"hypotheses_decision": "HYPOTHESES_NOT_REQUIRED", "research_hypotheses": [],
               "verification_result": {"verified": True, "verifier_status": "verified"}}
    assert _request(upstream_hypotheses=payload).hypotheses_not_required()


def test_six_categories_du_diagnostic_reel_lues():
    payload = {
        "diagnostic_status": "valide",
        "diagnosis": {
            "approche": {"code": "quantitative", "proposition": "Approche quantitative"},
            "logique": {"code": "hypothetico_deductive", "proposition": "Hypothético-déductif"},
            "type_recherche": {"code": "explicative", "proposition": "Recherche explicative"},
            "strategie": {"code": "enquete", "proposition": "Enquête par questionnaire"},
            "collecte": [{"code": "questionnaire", "proposition": "Questionnaire"}],
            "analyse": [{"code": "descriptif", "proposition": "Statistiques descriptives"}],
        },
        "verification_result": {"verified": True, "verifier_status": "verified"},
    }
    request = _request(upstream_methodology_diagnostic=payload)
    categories = request.diagnostic_categories()
    assert categories["approche"]["code"] == "quantitative"
    assert categories["collecte"][0]["code"] == "questionnaire"
    line = request.upstream_methodology_diagnostic.diagnostic_line()
    assert "approche" in line and "collecte" in line


# --- 3. des OBJETS là où le schéma attend des CHAÎNES ------------------------------------------
def test_objectifs_specifiques_en_objets_aplatis():
    payload = {"specific_objectives": [
        {"objectif": "Identifier les conditions", "code": "O1"},
        "Examiner la coordination"],
        "validation": {"verified": True, "verifier_status": "verified"}}
    objectives = _request(upstream_objectives=payload).effective_specific_objectives()
    assert len(objectives) == 2
    assert all(isinstance(o, str) for o in objectives)
    assert "Identifier les conditions" in objectives[0]


def test_listes_de_la_sortie_aplatissent_les_objets():
    output = MethodologyOutput.model_validate({
        "status": "needs_clarification",
        "informations_a_confirmer": [{"element": "effectif accessible", "pourquoi": "à recenser"}],
        "limits_of_this_output": ["limite simple"],
    })
    assert output.informations_a_confirmer == ["element : effectif accessible — pourquoi : à recenser"]
    assert output.limits_of_this_output == ["limite simple"]


# --- 4. les entrées de commodité tolèrent la sortie amont -------------------------------------
def test_reponses_precedentes_en_objets_aplaties():
    request = _request(previous_answers=[{"question": "taille ?", "reponse": "48"}])
    assert request.previous_answers == ["question : taille ? — reponse : 48"]


def test_diagnostic_absent_donne_des_chaines_vides_sans_lever():
    request = _request()
    assert request.effective_question() == ""
    assert request.effective_hypotheses() == []
    assert request.diagnostic_categories() == {}
    assert request.diagnostic_accepted() is False


# --- défauts constatés en CAMPAGNE RÉELLE (corrigés) -------------------------------------------
def test_une_chaine_seule_n_est_pas_eclatee_caractere_par_caractere():
    """Défaut réel : une chaîne au lieu d'une liste était itérée → « m », « o », « d »…"""
    from methodology_agent.schemas.common import flatten_strings
    assert flatten_strings("modalités à préciser") == ["modalités à préciser"]
    assert flatten_strings("") == []
    assert flatten_strings(None) == []
    assert flatten_strings(["a", "b"]) == ["a", "b"]


def test_modalites_et_conditions_restent_lisibles():
    """Le vérificateur a signalé des tableaux « éclatés caractère par caractère, illisibles »."""
    from methodology_agent.schemas.protocol import MethodeAnalyse, VariableIndicatrice
    indicateur = VariableIndicatrice.model_validate(
        {"nom": "intensité du télétravail", "nature": "variable",
         "modalites": "aucun jour ; 1-2 jours ; 3 jours et plus"})
    assert indicateur.modalites == ["aucun jour ; 1-2 jours ; 3 jours et plus"]
    analyse = MethodeAnalyse.model_validate(
        {"nom": "régression", "objet": "estimer la liaison",
         "conditions": "n > 30, variables continues, résidus normaux"})
    assert analyse.conditions[0].startswith("n > 30")


def test_manque_qui_nie_un_element_fourni_est_retire():
    """Le modèle déclarait « diagnostic de l'étape 8 absent » alors qu'il le lisait (C13)."""
    from methode_helpers import upstream_diagnostic

    from methodology_agent.pipeline.campaign import _clean_missing
    request = _request(upstream_methodology_diagnostic=upstream_diagnostic())
    items = ["Diagnostic méthodologique validé de l'étape 8 : absent du dossier.",
             "Accès au terrain non confirmé."]
    cleaned = _clean_missing(request, items)
    assert "Accès au terrain non confirmé." in cleaned
    assert all("absent du dossier" not in c for c in cleaned)


def test_trace_de_validation_derivee_des_faits(settings):
    from methode_helpers import StubLLM, upstream_diagnostic

    from methodology_agent.pipeline import campaign
    request = _request(subject_text="Le télétravail et la productivité des développeurs, 2020-2024",
                       upstream_methodology_diagnostic=upstream_diagnostic(),
                       academic_level="Master 2",
                       country="Côte d'Ivoire", geographical_area="Abidjan")
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    trace = result.output.trace_validation_diagnostic
    assert "en_attente_de_validation" in trace or "valide" in trace
    assert "vérifié par son vérificateur" in trace
