"""Intention de recherche : enum canonique et contrôle déterministe (SPEC §7, §9.2)."""

from research_question_agent.analysis import intent as intent_module
from research_question_agent.pipeline import intention_check
from research_question_agent.schemas.comprehension import Comprehension, ResearchIntention


def test_normalisation_aliases():
    assert intent_module.normalize_intent("Explication") == "expliquer"
    assert intent_module.normalize_intent("mesurer une relation") == "mesurer"
    assert intent_module.normalize_intent("comparaison") == "comparer"
    assert intent_module.normalize_intent("Examiner l'évolution") == "examiner_evolution"
    assert intent_module.normalize_intent("inconnu-total") == "autre"


def test_intention_inconnue_devient_autre():
    assert intent_module.normalize_intent("xyz") == "autre"
    assert intent_module.is_known("expliquer")


def test_intention_coherente_sans_ambiguite():
    intention = ResearchIntention(intention="expliquer", justification="Découle de la problématique.",
                                 alternatives=[])
    result = intention_check.check(intention, Comprehension(), "problématique")
    assert result["issues"] == []
    assert result["ambiguous"] is False


def test_intentions_concurrentes_signalees():
    intention = ResearchIntention(intention="mesurer", justification="Mesurer la relation.",
                                  alternatives=["comprendre"])
    result = intention_check.check(intention, Comprehension(), "problématique")
    assert result["ambiguous"] is True
    assert result["clarification_question"]
