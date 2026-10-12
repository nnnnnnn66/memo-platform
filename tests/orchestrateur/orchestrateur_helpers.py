"""Aides partagées des tests de l'orchestrateur — hors `conftest.py`, et c'est volontaire.

Défaut corrigé : `avancer` vivait dans `conftest.py`, et `test_orchestrateur_03_campagne.py`
l'importait par `from conftest import avancer`. Or `tests/site_web/conftest.py` porte le MÊME nom
de module : selon l'ordre de collecte, l'import tombait sur l'un ou sur l'autre, et la suite
passait ou échouait sans qu'aucune ligne de code n'ait changé. Un test qui dépend de l'ordre de
collecte n'est pas un test.

D'où la convention du projet : les aides partagées vivent dans un module au nom UNIQUE
(`<sujet>_helpers.py`), et les fixtures restent dans `conftest.py`.
"""


def avancer(settings, etudiant, session, agent, nombre=1, decision="accepted"):
    """Fait avancer un dossier de `nombre` étapes (lancer puis décider), pour les tests."""
    from orchestrator.pipeline import campaign

    for _ in range(nombre):
        campaign.lancer_etape(settings, etudiant, session, transport=agent)
        campaign.decider(settings, etudiant, session, decision, transport=agent)
    return campaign.etat(settings, etudiant, session)
