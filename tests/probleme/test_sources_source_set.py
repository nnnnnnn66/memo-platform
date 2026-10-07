"""SourceSet : identification stable, dédoublonnage, bloc transmis au LLM."""

from research_problem_agent.sources.source_set import SourceSet


def _record(**overrides):
    base = {
        "source": "Revue X", "title": "Titre", "url": "https://doi.org/10.1/a",
        "doi": "10.1/a", "publication_date": "2021-01-01", "snippet": "extrait",
    }
    base.update(overrides)
    return base


def test_identifiants_stables_et_sequentiels():
    source_set = SourceSet()
    source_set.add("openalex", _record(), "scientific", 1200)
    source_set.add("crossref", _record(url="https://doi.org/10.1/b", doi="10.1/b"),
                   "scientific", 1200)

    assert [r.source_id for r in source_set.records] == ["S1", "S2"]
    assert source_set.by_id("S2").doi == "10.1/b"


def test_dedoublonnage_par_doi_puis_url():
    source_set = SourceSet()
    source_set.add("openalex", _record(), "scientific", 1200)
    source_set.add("crossref", _record(), "scientific", 1200)                    # même DOI
    source_set.add("doaj", _record(doi="", url="https://doi.org/10.1/a"),
                   "scientific", 1200)                                          # même URL
    source_set.add("hal", _record(doi="", url="https://hal.science/x", title="Autre"),
                   "scientific", 1200)

    assert len(source_set) == 2
    assert source_set.providers_used == ["openalex", "hal"]


def test_extrait_borne_par_la_limite_configuree():
    source_set = SourceSet()
    source_set.add("openalex", _record(snippet="x" * 5000), "scientific", 100)
    assert len(source_set.records[0].snippet) == 100


def test_bloc_transmis_est_balise_non_fiable():
    source_set = SourceSet()
    source_set.add("openalex", _record(), "scientific", 1200)
    block = source_set.to_prompt_block()

    assert block.startswith("<source_web_non_fiable>")
    assert block.rstrip().endswith("</source_web_non_fiable>")
    assert "[S1]" in block and "https://doi.org/10.1/a" in block


def test_bloc_sans_source_interdit_de_citer():
    block = SourceSet().to_prompt_block()
    assert "AUCUNE source" in block
    assert "<source_web_non_fiable>" in block


def test_provider_en_echec_enregistre_sans_invention():
    source_set = SourceSet()
    source_set.mark_failed("doaj", "TOOL_ERROR: HTTP 503")

    assert len(source_set) == 0
    assert source_set.providers_failed[0]["provider"] == "doaj"
    assert "503" in source_set.providers_failed[0]["reason"]
