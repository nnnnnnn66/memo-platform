"""Lecture du texte intégral : sections, passages, couche texte, ancrage verbatim, sûreté réseau."""

import pytest

from literature_review_agent.core.errors import ErrorState, PipelineError
from literature_review_agent.sources.fulltext import (
    Page,
    build_excerpts,
    clean_extracted,
    dedupe_sections,
    has_text_layer,
    is_quote_anchored,
    split_sections,
)
from literature_review_agent.sources.http import FileDownloader

TEXTE = """Résumé
Cette étude examine le télétravail et la productivité des développeurs sur un terrain ivoirien.

1. Introduction
Le télétravail s'est généralisé depuis 2020 dans les entreprises de services numériques.

2. Méthodologie
Nous avons administré un questionnaire à 120 développeurs d'Abidjan entre mars et juin 2023.

3. Résultats
La productivité perçue augmente de 4 % en moyenne, mais l'effet dépend fortement de
l'organisation du travail et de la qualité de la connexion internet.

4. Discussion
Ces résultats rejoignent la littérature internationale tout en soulignant des contraintes locales.

5. Limites
L'échantillon reste restreint et repose sur des mesures déclaratives.

Conclusion
Le télétravail partiel semble soutenable si l'organisation est adaptée au contexte local.
"""


def _pages(text: str) -> list[Page]:
    return [Page(number=1, text=text)]


def test_decoupage_en_sections():
    sections = dedupe_sections(split_sections(_pages(TEXTE)))
    names = [name for name, _, _ in sections]
    assert "abstract" in names
    assert "method" in names
    assert "results" in names
    assert "limits" in names
    method = dict((name, text) for name, _, text in sections)["method"]
    assert "questionnaire" in method


def test_extraction_des_passages_prioritaires():
    sections = dedupe_sections(split_sections(_pages(TEXTE)))
    excerpts = build_excerpts(sections, window=4000, max_excerpts=3)
    assert excerpts
    assert excerpts[0]["section"] in ("method", "results", "limits")
    assert all(excerpt["page"] == 1 for excerpt in excerpts)


def test_detection_absence_de_couche_texte():
    assert has_text_layer(_pages(TEXTE)) is True
    assert has_text_layer(_pages("")) is False
    assert has_text_layer([Page(number=1, text="...")]) is False


def test_ancrage_verbatim():
    citation = "Nous avons administré un questionnaire à 120 développeurs d'Abidjan"
    assert is_quote_anchored(citation, TEXTE) is True
    # citation longue coupée par une mise en page : les segments restent retrouvés
    longue = ("La productivité perçue augmente de 4 % en moyenne, mais l'effet dépend fortement de\n"
              "l'organisation du travail et de la qualité de la connexion internet.")
    assert is_quote_anchored(longue, TEXTE) is True
    inventee = "L'étude montre une hausse de 42 % de la productivité nationale en 1998."
    assert is_quote_anchored(inventee, TEXTE) is False
    assert is_quote_anchored("trop court", TEXTE) is False
    # régression : une citation inventée de 25 à 60 caractères était acceptée à tort
    inventee_courte = "Cette phrase n'apparaît nulle part dans le document."
    assert is_quote_anchored(inventee_courte, TEXTE) is False


def test_nettoyage_du_texte_extrait():
    brut = "télétra-\nvail   et\n\n\n productivité\u00ad"
    # Les césures sont recollées, le tiret conditionnel retiré, les espaces multiples réduits ;
    # les retours à la ligne sont CONSERVÉS (ils servent au découpage en sections).
    assert clean_extracted(brut, 200) == "télétravail et\n\n productivité"
    assert clean_extracted(brut, 5) == "télét"


# --- sûreté du téléchargement (anti-SSRF, bornes) -----------------------------------------------

class _Cfg(dict):
    pass


def _downloader(settings, **overrides):
    cfg = dict(settings.sources)
    cfg.update(overrides)
    return FileDownloader(cfg, settings.fulltext, settings.limits)


def test_http_refuse(settings):
    downloader = _downloader(settings)
    with pytest.raises(PipelineError) as exc:
        downloader.download_pdf("http://repository.example/a.pdf")
    assert exc.value.state == ErrorState.SECURITY_VIOLATION


@pytest.mark.parametrize("url", [
    "https://localhost/a.pdf",
    "https://127.0.0.1/a.pdf",
    "https://169.254.169.254/latest/meta-data/",
    "https://serveur.local/a.pdf",
])
def test_adresses_non_publiques_refusees(settings, url):
    downloader = _downloader(settings)
    with pytest.raises(PipelineError) as exc:
        downloader.download_pdf(url)
    assert exc.value.state == ErrorState.SECURITY_VIOLATION


def test_non_pdf_refuse(settings, monkeypatch):
    import literature_review_agent.sources.http as http_module

    class _Resp:
        def read(self, _n=None):
            return b"<html>pas un pdf</html>"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(http_module, "open_checked",
                        lambda check, request, timeout=None: _Resp())
    monkeypatch.setattr(http_module, "_is_public_ip", lambda host: True)
    downloader = _downloader(settings)
    with pytest.raises(PipelineError) as exc:
        downloader.download_pdf("https://repository.example/a.pdf")
    assert exc.value.state == ErrorState.TOOL_ERROR
    assert "PDF" in exc.value.detail


def test_plafond_de_telechargements(settings, monkeypatch):
    import literature_review_agent.sources.http as http_module

    class _Resp:
        def read(self, _n=None):
            return b"%PDF-1.4 contenu minimal"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(http_module, "open_checked",
                        lambda check, request, timeout=None: _Resp())
    monkeypatch.setattr(http_module, "_is_public_ip", lambda host: True)
    downloader = _downloader(settings)
    for _ in range(settings.limits.max_downloads):
        downloader.download_pdf("https://repository.example/a.pdf")
    with pytest.raises(PipelineError) as exc:
        downloader.download_pdf("https://repository.example/b.pdf")
    assert exc.value.state == ErrorState.RESOURCE_LIMIT


# --- reprise sur erreur transitoire des API (429 / 5xx) ------------------------------------------

def test_nouvelle_tentative_sur_429(settings, monkeypatch):
    import urllib.error

    import literature_review_agent.sources.http as http_module

    class _Resp:
        def read(self, _n=None):
            return b'{"results": []}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    calls = {"n": 0}

    def fake_open(check, request, timeout=None):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        return _Resp()

    monkeypatch.setattr(http_module, "open_checked", fake_open)
    monkeypatch.setattr(http_module.time, "sleep", lambda _s: None)

    cfg = dict(settings.sources)
    cfg.update({"retry_on_transient": 2, "polite_delay_seconds": 0})
    fetcher = http_module.ApiFetcher(cfg, settings.limits, {"api.openalex.org"})
    payload = fetcher.fetch_json("https://api.openalex.org/works", {"search": "x"})

    assert payload == {"results": []}
    assert calls["n"] == 3, "l'API doit être réessayée après un 429"
    assert fetcher.requests == 3, "chaque tentative consomme le budget réseau (honnêteté du compte)"


def test_429_persistant_declare_l_echec(settings, monkeypatch):
    import urllib.error

    import literature_review_agent.sources.http as http_module

    def fake_open(check, request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(http_module, "open_checked", fake_open)
    monkeypatch.setattr(http_module.time, "sleep", lambda _s: None)

    cfg = dict(settings.sources)
    cfg.update({"retry_on_transient": 1, "polite_delay_seconds": 0})
    fetcher = http_module.ApiFetcher(cfg, settings.limits, {"api.openalex.org"})
    with pytest.raises(PipelineError) as exc:
        fetcher.fetch_json("https://api.openalex.org/works", {"search": "x"})
    assert exc.value.state == ErrorState.TOOL_ERROR
    assert "429" in exc.value.detail
