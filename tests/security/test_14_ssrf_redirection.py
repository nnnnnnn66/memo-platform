"""Anti-SSRF par redirection HTTP : chaque saut est revalidé.

Chaîne d'attaque : le client réseau ne contrôlait QUE l'URL initiale (liste blanche des
fournisseurs + refus des adresses privées). `urllib.request.urlopen` suivait ensuite les
redirections par défaut, sans repasser par le contrôle : un fournisseur — ou un lien qu'il
renvoie — pouvait rediriger la requête vers 127.0.0.1, 169.254.169.254 (métadonnées d'instance) ou
tout autre service interne. Démontré en local avant correction : urlopen suivait bien la
redirection vers un second hôte non autorisé.
"""

import urllib.request

import pytest

from problematization_agent.core.errors import ErrorState, PipelineError
from problematization_agent.sources.http import _CheckedRedirectHandler, open_checked

ALLOWED = "https://api.openalex.org/works"


def _check(url: str) -> None:
    """Contrôle factice, calqué sur celui des agents : seul le fournisseur déclaré est autorisé."""
    if not url.startswith("https://api.openalex.org"):
        raise PipelineError(ErrorState.SECURITY_VIOLATION, f"hôte non autorisé : {url}")


def test_redirection_vers_hote_non_autorise_refusee():
    handler = _CheckedRedirectHandler(_check)
    request = urllib.request.Request(ALLOWED)
    with pytest.raises(PipelineError) as exc:
        handler.redirect_request(request, None, 302, "Found", {}, "http://127.0.0.1:9102/interne")
    assert exc.value.state == ErrorState.SECURITY_VIOLATION


def test_redirection_vers_metadonnees_instance_refusee():
    """169.254.169.254 rend les identifiants d'instance : cible classique d'un SSRF."""
    handler = _CheckedRedirectHandler(_check)
    request = urllib.request.Request(ALLOWED)
    with pytest.raises(PipelineError):
        handler.redirect_request(request, None, 302, "Found", {},
                                 "http://169.254.169.254/latest/meta-data/")


def test_redirection_vers_hote_autorise_acceptee():
    handler = _CheckedRedirectHandler(_check)
    request = urllib.request.Request(ALLOWED)
    following = handler.redirect_request(request, None, 302, "Found", {},
                                         "https://api.openalex.org/works?page=2")
    assert following is not None


def test_open_checked_existe_pour_tous_les_agents():
    """Chaque client réseau expose le même garde-fou (aucune copie restée sans contrôle)."""
    from importlib import import_module

    for agent in ("literature_review_agent", "methodology_diagnostic_agent",
                  "problematization_agent", "research_hypotheses_agent",
                  "research_objectives_agent", "research_problem_agent",
                  "research_question_agent"):
        module = import_module(f"{agent}.sources.http")
        assert callable(getattr(module, "open_checked", None)), agent
        assert getattr(module, "_CheckedRedirectHandler", None) is not None, agent


def test_les_clients_agent_n_appellent_plus_urlopen_directement():
    """Régression : un `urllib.request.urlopen` direct réintroduirait la faille."""
    import pathlib

    for path in pathlib.Path("src").glob("*/sources/http.py"):
        code = "\n".join(
            line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith(("#", '"', "'", "`", "*"))
        )
        assert "urllib.request.urlopen(" not in code, f"appel direct restant : {path}"
