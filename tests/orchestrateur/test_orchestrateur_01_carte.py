"""La carte du parcours : cohérence de la configuration elle-même (aucun réseau, aucun modèle)."""

import pytest

from orchestrator.core.config import Etape, charger


def test_treize_etapes_declarees(settings):
    """11 agents + la vérification globale = 12 entrées, ordonnées."""
    numeros = [etape.numero for etape in settings.etapes]
    assert numeros == list(range(1, 12)) + [13]
    assert numeros == sorted(numeros)


def test_chaque_etape_a_un_agent_un_port_et_une_route(settings):
    for etape in settings.etapes:
        assert etape.agent and etape.prefixe.startswith("/")
        assert etape.route_analyse.startswith("/")
        assert 1024 < etape.port < 65536


def test_aucune_etape_ne_depend_du_futur(settings):
    """Le pont ne peut venir que d'une étape ANTÉRIEURE : sinon le parcours est impossible."""
    for etape in settings.etapes:
        for champ, source in etape.upstream.items():
            assert source < etape.numero, f"étape {etape.numero} attend l'étape {source}"


def test_derniere_etape_est_la_verification_globale(settings):
    assert settings.etapes[-1].finale is True
    assert settings.etapes[-1].agent == "research_coherence_verifier"
    # Elle reçoit les 11 sorties : même mécanisme que les autres étapes.
    assert sorted(settings.etapes[-1].upstream.values()) == list(range(1, 12))


def test_suivante_respecte_le_parcours(settings):
    assert settings.suivante(1).numero == 2
    assert settings.suivante(11).numero == 13
    assert settings.suivante(13) is None
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


def test_url_par_etape(settings):
    etape = settings.par_numero[4]
    assert etape.url_analyse("127.0.0.1") == "http://127.0.0.1:8040/problematique/analyze"
    assert etape.url_lecture("127.0.0.1", "e", "s") == "http://127.0.0.1:8040/problematique/e/s"
    assert etape.url_decision("127.0.0.1", "e", "s") == "http://127.0.0.1:8040/problematique/e/s/decision"
