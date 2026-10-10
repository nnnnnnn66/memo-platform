"""Passation RÉELLE entre agents : les sorties telles que les étapes amont les produisent VRAIMENT.

Ces tests sont nés d'un échec de chaîne réel : les fixtures fabriquées à la main portaient les clés
ATTENDUES (`validation`) et non les clés RÉELLEMENT produites (`verification_result`), si bien que la
suite passait au vert pendant que la chaîne refusait la sortie de l'agent 5 comme « non vérifiée ».
Règle : toute fixture de passation doit copier une sortie réelle, champ pour champ.
"""


def test_question_amont_verification_result_acceptee():
    """L'agent 5 publie `verification_result` : sa sortie doit être reconnue VÉRIFIÉE."""
    from research_hypotheses_agent.schemas.input import HypothesesRequest
    payload = {
        "agent": "research_question_agent",
        "version": "1.0",
        "status": "validated",
        "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité "
                                  "des développeurs d'Abidjan ?",
        "secondary_research_questions": ["Quels facteurs modèrent cette relation ?"],
        "verification_result": {"verified": True, "verifier_status": "verified"},
    }
    req = HypothesesRequest(student_id="e", discipline="Gestion", upstream_question=payload)
    assert req.upstream_question.is_verified
    assert "télétravail" in req.effective_question().lower()


def test_objectifs_amont_verification_result_acceptee():
    from research_hypotheses_agent.schemas.input import HypothesesRequest
    payload = {
        "agent": "research_objectives_agent",
        "status": "awaiting_human_validation",
        "general_objective": "Analyser la relation entre le télétravail et la productivité.",
        "specific_objectives": ["Identifier les conditions de travail associées."],
        "verification_result": {"verified": True, "verifier_status": "verified"},
    }
    req = HypothesesRequest(student_id="e", discipline="Gestion", upstream_objectives=payload)
    assert req.upstream_objectives.is_verified
    assert req.effective_general_objective()


def test_amont_non_verifie_toujours_refuse():
    """La tolérance ne doit PAS accepter une sortie dont le vérificateur a échoué."""
    from research_hypotheses_agent.schemas.input import HypothesesRequest
    payload = {"general_objective": "objet", "specific_objectives": [],
               "verification_result": {"verified": False, "verifier_status": "pending"}}
    req = HypothesesRequest(student_id="e", discipline="Gestion", upstream_objectives=payload)
    assert not req.upstream_objectives.is_verified


def test_validation_ancienne_forme_toujours_acceptee():
    """Les agents 1 à 4 publient sous `validation` : la tolérance doit garder les deux formes."""
    from research_hypotheses_agent.schemas.input import HypothesesRequest
    payload = {"general_objective": "objet", "specific_objectives": [],
               "validation": {"verified": True, "verifier_status": "verified"}}
    req = HypothesesRequest(student_id="e", discipline="Gestion", upstream_objectives=payload)
    assert req.upstream_objectives.is_verified


def test_appuis_et_preuves_en_objets_acceptes():
    """Le modèle renvoie parfois des OBJETS dans les listes de chaînes : la campagne ne doit pas
    échouer (17 erreurs de validation, deux tentatives de suite, constaté en exécution réelle)."""
    from research_hypotheses_agent.schemas.stages import FormulationOutput
    out = FormulationOutput.model_validate({
        "theoretical_or_literature_support": [
            {"source": "D54", "appui": "le télétravail réduit la coordination", "pour": ["H1", "H2"]},
            "D12 — appui direct",
        ],
        "required_evidence": [{"hypothesis_id": "H1", "evidence": "observations sur la coordination"}],
    })
    assert out.theoretical_or_literature_support == [
        "source : D54 — appui : le télétravail réduit la coordination — pour : H1, H2",
        "D12 — appui direct",
    ]
    assert out.required_evidence == ["hypothesis_id : H1 — evidence : observations sur la coordination"]


def test_chaines_simples_inchangees():
    from research_hypotheses_agent.schemas.stages import FormulationOutput
    out = FormulationOutput.model_validate({
        "theoretical_or_literature_support": ["D54 — appui"],
        "required_evidence": ["mesure de productivité"],
    })
    assert out.theoretical_or_literature_support == ["D54 — appui"]
    assert out.required_evidence == ["mesure de productivité"]
