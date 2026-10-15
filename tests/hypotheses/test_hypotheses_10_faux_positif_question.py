"""« qui », « quelle », « quand » ne font pas d'une proposition une question.

Défaut réel constaté en rejouant le dossier de démonstration : la règle comptait les marqueurs
interrogatifs PARTOUT dans la formulation. « les secteurs QUI ont accueilli des opérations… » et
« QUELLE que soit la période… » étaient donc déclarées « c'est une question, pas une proposition »,
les deux tentatives échouaient et la campagne mourait sans même atteindre le vérificateur
(« phase non conforme : hypothèse 2 : c'est une question »).

Ne comptent désormais qu'un point d'interrogation, ou un marqueur en TÊTE de formulation.
"""
import pytest

from research_hypotheses_agent.analysis.hypothesis_rules import looks_like_question


@pytest.mark.parametrize("formulation", [
    "Les secteurs de Bingerville qui ont accueilli des opérations de promotion immobilière "
    "présentent une régression du couvert végétal plus marquée.",
    "Les transformations environnementales s'intensifient à partir de l'implantation, quelle que "
    "soit la période retenue.",
    "Le suivi environnemental, quand il existe, reste moins formalisé que le suivi foncier.",
])
def test_une_proposition_n_est_pas_une_question(formulation):
    assert not looks_like_question(formulation)


@pytest.mark.parametrize("formulation", [
    "Quelle est la part attribuable aux opérations immobilières ?",
    "Pourquoi la végétation recule-t-elle dans les secteurs lotis ?",
    "Comment les promoteurs prennent-ils en compte les contraintes environnementales",
])
def test_une_vraie_question_est_reconnue(formulation):
    assert looks_like_question(formulation)
