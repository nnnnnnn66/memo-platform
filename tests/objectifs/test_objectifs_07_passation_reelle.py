"""Passation RÉELLE vers l'agent 6 : sorties telles que les étapes amont les produisent VRAIMENT.

Né d'un échec de chaîne réel : l'agent 6 lisait `upstream_problem.research_problem` (l'agent 2 publie
`identified_problem.statement`) et `upstream_problematic.validated_problematic` (l'agent 4 publie
`problematique_note.texte_complet`) — la passation 2 -> 6 échouait sur un AttributeError, et les
fixtures fabriquées à la main ne le voyaient pas parce qu'elles portaient les clés ATTENDUES.
"""


def _objectifs_request(**kw):
    from research_objectives_agent.schemas.input import ObjectivesRequest
    return ObjectivesRequest(student_id="e", discipline="Gestion", **kw)


def test_question_amont_verification_result_acceptee():
    """L'agent 5 publie `verification_result`, pas `validation`."""
    payload = {
        "agent": "research_question_agent", "status": "validated",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité ?",
        "secondary_research_questions": ["Quels facteurs modèrent la relation ?"],
        "verification_result": {"verified": True, "verifier_status": "verified"},
    }
    req = _objectifs_request(upstream_question=payload)
    assert req.upstream_question.is_verified
    assert "télétravail" in req.effective_question().lower()


def test_probleme_lu_dans_identified_problem_statement():
    """Forme réelle de la sortie de l'agent 2 : `identified_problem.statement`."""
    payload = {
        "agent": "research_problem_agent", "status": "awaiting_human_validation",
        "identified_problem": {"statement": "Le turnover des développeurs s'aggrave depuis 2020.",
                               "provenance": "provided"},
        "validation": {"verified": True, "verifier_status": "verified"},
    }
    req = _objectifs_request(upstream_problem=payload)
    assert req.effective_problem() == "Le turnover des développeurs s'aggrave depuis 2020."


def test_problematique_lue_dans_problematique_note():
    """Forme réelle de la sortie de l'agent 4 : `problematique_note.texte_complet`."""
    payload = {
        "agent": "problematization_agent", "status": "awaiting_human_validation",
        "problematique_note": {"texte_complet": "Le télétravail, loin de résoudre la question…",
                               "sections": []},
        "validation": {"verified": True, "verifier_status": "verified"},
    }
    req = _objectifs_request(upstream_problematic=payload)
    assert req.effective_problematic() == "Le télétravail, loin de résoudre la question…"


def test_problematique_reprise_de_la_question_quand_absente():
    """À défaut de la sortie de l'agent 4, celle de l'agent 5 porte `validated_problematic`."""
    payload = {
        "agent": "research_question_agent", "status": "validated",
        "validated_problematic": "Problématique validée reprise par l'agent 5.",
        "main_research_question": "Question ?",
        "verification_result": {"verified": True, "verifier_status": "verified"},
    }
    req = _objectifs_request(upstream_question=payload)
    assert req.effective_problematic() == "Problématique validée reprise par l'agent 5."


def test_amont_non_verifie_toujours_refuse():
    payload = {"main_research_question": "Question ?",
               "verification_result": {"verified": False, "verifier_status": "pending"}}
    req = _objectifs_request(upstream_question=payload)
    assert not req.upstream_question.is_verified


def test_probleme_vide_ne_leve_pas():
    """Un amont incomplet doit rendre une chaîne vide, jamais lever (l'agent analyse alors l'absence)."""
    req = _objectifs_request(upstream_problem={"agent": "research_problem_agent"})
    assert req.effective_problem() == ""
    assert req.effective_problematic() == ""
