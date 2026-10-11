"""La carte du parcours : cohérence de la configuration elle-même (aucun réseau, aucun modèle).

L'ORDRE DE DÉCLARATION fait foi. Les numéros d'étape restent des identifiants internes stables
(le 12 est réservé), ce qui permet de placer la vérification globale AVANT la conclusion.
"""

import pytest

from orchestrator.core.config import charger


def test_douze_etapes_declarees(settings):
    """11 étapes d'analyse + la vérification globale = 12 entrées."""
    numeros = [etape.numero for etape in settings.etapes]
    assert len(numeros) == 12
    assert numeros == list(range(1, 11)) + [13, 11]


def test_chaque_etape_a_un_agent_un_port_et_une_route(settings):
    for etape in settings.etapes:
        assert etape.agent and etape.prefixe.startswith("/")
        assert etape.route_analyse.startswith("/")
        assert 1024 < etape.port < 65536


def test_aucune_etape_ne_depend_du_futur(settings):
    """Le pont ne peut venir que d'une étape ANTÉRIEURE DANS LE PARCOURS."""
    positions = {etape.numero: rang for rang, etape in enumerate(settings.etapes)}
    for etape in settings.etapes:
        for champ, source in etape.upstream.items():
            assert positions[source] < positions[etape.numero], \
                f"étape {etape.numero} attend l'étape {source}, qui vient après elle"


def test_la_verification_globale_vient_avant_la_conclusion(settings):
    """Décision du porteur : on vérifie que le dossier tient debout, PUIS on rédige la conclusion.

    Conséquence assumée : le vérificateur n'audite plus la conclusion, qui n'existe pas encore.
    """
    ordre = [etape.numero for etape in settings.etapes]

    assert ordre.index(13) < ordre.index(11)
    assert 11 not in settings.par_numero[13].upstream.values()
    assert sorted(settings.par_numero[13].upstream.values()) == list(range(1, 11))


def test_la_conclusion_est_la_derniere_etape(settings):
    derniere = settings.etapes[-1]

    assert derniere.finale is True
    assert derniere.agent == "research_conclusion_agent"


def test_suivante_respecte_le_parcours(settings):
    assert settings.suivante(1).numero == 2
    assert settings.suivante(10).numero == 13
    assert settings.suivante(13).numero == 11
    assert settings.suivante(11) is None
    assert settings.suivante(999) is None


def test_configuration_invalide_refusee(tmp_path):
    """Une dépendance vers une étape inexistante doit être refusée AU DÉMARRAGE."""
    fichier = tmp_path / "mauvais.yaml"
    fichier.write_text(
        "transport: {mode: http}\netapes:\n"
        "  - {numero: 1, agent: a, libelle: L, port: 9001, prefixe: /a, route_analyse: /a/x}\n"
        "  - {numero: 2, agent: b, libelle: L, port: 9002, prefixe: /b, route_analyse: /b/x,"
        " upstream: {upstream_subject: 7}}\n",
        encoding="utf-8")
    with pytest.raises(ValueError):
        charger(fichier)


def test_une_dependance_vers_une_etape_posterieure_est_refusee(tmp_path):
    """Le pont doit remonter le temps DU PARCOURS, pas le descendre."""
    fichier = tmp_path / "inverse.yaml"
    fichier.write_text(
        "transport: {mode: http}\netapes:\n"
        "  - {numero: 3, agent: a, libelle: L, port: 9001, prefixe: /a, route_analyse: /a/x,"
        " upstream: {upstream_amont: 5}}\n"
        "  - {numero: 5, agent: b, libelle: L, port: 9002, prefixe: /b, route_analyse: /b/x}\n",
        encoding="utf-8")
    with pytest.raises(ValueError):
        charger(fichier)


def test_url_par_etape(settings):
    etape = settings.par_numero[4]
    assert etape.url_analyse("127.0.0.1") == "http://127.0.0.1:8040/problematique/analyze"
    assert etape.url_lecture("127.0.0.1", "e", "s") == "http://127.0.0.1:8040/problematique/e/s"
    assert etape.url_decision("127.0.0.1", "e", "s") == \
        "http://127.0.0.1:8040/problematique/e/s/decision"
