"""Anti-fusion, honnêteté et garde anti auto-validation."""

from problematique_helpers import StubLLM

from problematization_agent.pipeline import business_validation, campaign
from problematization_agent.schemas.common import SubjectReference
from problematization_agent.schemas.output import (
    ProblemStatus,
    ProblematizationOutput,
    ProblematiqueNote,
)
from problematization_agent.schemas.input import ProblemRequest


def _request() -> ProblemRequest:
    return ProblemRequest(student_id="etu-1", subject_text="Sujet de test",
                          discipline="Gestion", academic_level="Master 2")


def test_marqueur_de_fusion_detecte():
    output = ProblematizationOutput(
        status=ProblemStatus.ready_for_verification,
        subject_reference=SubjectReference(original="Sujet de test"),
        problematique_note=ProblematiqueNote(texte_complet="Les hypothèses de recherche sont ..."),
    )
    violations = business_validation.validate_semantics(output, _request(), _FakeIndex())
    assert any("fusion interdite" in v for v in violations)


def test_une_phrase_qui_NIE_la_fusion_n_est_pas_une_fusion():
    """DÉFAUT RÉEL du premier parcours de bout en bout, sur un vrai mémoire.

    Le modèle écrivait exactement ce que la règle demande — que la proposition ne préempte PAS la
    question de recherche définitive — et la recherche de sous-chaîne faisait échouer l'étape. Le
    parcours s'arrêtait à l'étape 4, sur une réponse JUSTE.
    """
    output = ProblematizationOutput(
        status=ProblemStatus.ready_for_verification,
        subject_reference=SubjectReference(original="Sujet de test"),
        problematique_note=ProblematiqueNote(texte_complet=(
            "Il s'agit d'une proposition de problématisation, destinée à être discutée, amendée ou "
            "écartée avec le directeur de mémoire ; elle ne préjuge ni de la question de recherche "
            "définitive, ni des objectifs, ni du dispositif d'enquête, qui relèvent des étapes "
            "ultérieures.")),
    )

    violations = business_validation.validate_semantics(output, _request(), _FakeIndex())

    assert not any("fusion interdite" in violation for violation in violations), violations


def test_une_phrase_qui_AFFIRME_la_fusion_reste_refusee():
    """Le garde-fou n'est pas relâché pour autant : affirmer la chose la fait toujours échouer."""
    output = ProblematizationOutput(
        status=ProblemStatus.ready_for_verification,
        subject_reference=SubjectReference(original="Sujet de test"),
        problematique_note=ProblematiqueNote(
            texte_complet="La question de recherche définitive est désormais arrêtée."),
    )

    violations = business_validation.validate_semantics(output, _request(), _FakeIndex())

    assert any("fusion interdite" in violation for violation in violations), violations


def test_auto_validation_interdite():
    output = ProblematizationOutput(status=ProblemStatus.ready_for_verification,
                                    subject_reference=SubjectReference(original="Sujet de test"))
    output.validation.verified = True
    violations = business_validation.validate_semantics(output, _request(), _FakeIndex())
    assert any("R8" in v for v in violations)


def test_needs_clarification_sans_question_est_invalide():
    output = ProblematizationOutput(status=ProblemStatus.needs_clarification,
                                    subject_reference=SubjectReference(original="Sujet de test"))
    violations = business_validation.validate_final(output)
    assert any("R9" in v for v in violations)


def test_campagne_ne_s_auto_valide_pas_avant_le_verificateur(settings, request_factory):
    """Sans vérificateur disponible (réponse vide), l'agent n'a jamais posé verified lui-même."""
    from problematization_agent.pipeline import campaign as campaign_module

    result = campaign_module.run(request_factory(), settings,
                                 StubLLM(verifier={"agent": "problematique_verifier",
                                                   "version": "1.0", "verdict": "rejected",
                                                   "controls": [], "corrections": [], "flags": []}),
                                 allow_network=False)
    assert result.verifier_status == "rejected"
    assert result.output.validation.verified is False


class _FakeIndex:
    doc_ids = {"D1"}
    documents = {}

    def quote_ok(self, doc_id, quote, min_chars=25):
        return True
