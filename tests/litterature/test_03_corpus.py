"""Corpus documentaire : dédoublonnage, notation, langues, détection géographique."""

from literature_review_agent.sources.corpus import (
    Corpus,
    CorpusRecord,
    detect_geography,
    normalize_language,
)


def _record(**overrides) -> CorpusRecord:
    payload = {
        "provider": "crossref", "source_type": "scientific", "document_type": "article",
        "title": "Telework and productivity", "url": "https://doi.org/10.1/a", "doi": "10.1/a",
        "year": 2021, "authors": ["Jane Doe"], "abstract": "telework productivity evidence",
        "language": "en",
    }
    payload.update(overrides)
    return CorpusRecord(**payload)


def test_doublon_doi_ecarte():
    corpus = Corpus()
    assert corpus.add(_record()) is True
    assert corpus.add(_record(provider="openalex")) is False
    assert len(corpus) == 1
    assert corpus.duplicates_removed == 1


def test_doublon_par_titre_et_auteur():
    corpus = Corpus()
    corpus.add(_record())
    assert corpus.add(_record(doi="", url="https://openalex.org/W9")) is False


def test_document_sans_doi_ni_url_non_citable():
    corpus = Corpus()
    assert corpus.add(_record(doi="", url="")) is False
    assert len(corpus) == 0


def test_identifiants_stables():
    corpus = Corpus()
    corpus.add(_record())
    corpus.add(_record(title="Autre", doi="10.2/b", url="https://doi.org/10.2/b"))
    assert [r.doc_id for r in corpus.records] == ["D1", "D2"]


def test_notation_favorise_recouvrement_et_acces_libre():
    corpus = Corpus()
    corpus.add(_record(doi="10.1/a", url="https://doi.org/10.1/a",
                       title="Telework productivity", abstract="telework productivity gains",
                       is_oa=True))
    corpus.add(_record(doi="10.2/b", url="https://doi.org/10.2/b", title="Cuisine tropicale",
                       abstract="recettes", is_oa=False))
    corpus.rank(["telework", "productivity"], ["en"])
    assert corpus.records[0].doi == "10.1/a"
    assert corpus.records[0].relevance > corpus.records[1].relevance


def test_langues_normalisees():
    assert normalize_language("eng") == "en"
    assert normalize_language("fre") == "fr"
    assert normalize_language("FRA") == "fr"
    assert normalize_language("unknown") == ""
    assert normalize_language("") == ""


def test_geographie_detectee_avec_preuve():
    scope, evidence = detect_geography("Le télétravail à Abidjan en Côte d'Ivoire")
    assert scope == "ivory_coast"
    assert "côte d'ivoire" in evidence.lower() or "abidjan" in evidence.lower()

    assert detect_geography("Telework in Spain")[0] == "unclear"
    assert detect_geography("Étude en Afrique de l'Ouest")[0] == "west_africa"


def test_comptages_et_bloc_prompt():
    corpus = Corpus()
    corpus.add(_record(abstract="telework gains"))
    corpus.rank(["telework"], ["en"])
    counts = corpus.counts()
    assert counts["by_language"] == {"en": 1}
    assert counts["by_type"] == {"article": 1}
    block = corpus.to_prompt_block()
    assert "<contenu_recolte_non_fiable>" in block
    assert "D1" in block


def test_notation_renseigne_les_concepts_recoupes():
    """Le nombre de concepts recoupés sert de garde de pertinence décorrélé du modèle."""
    corpus = Corpus()
    corpus.add(_record(title="Telework and productivity", abstract="telework productivity"))
    corpus.add(_record(title="Cuisine tropicale", abstract="recettes de cuisine",
                       doi="10.9/z", url="https://doi.org/10.9/z"))
    corpus.rank(["telework", "productivity", "télétravail"], ["en"])
    by_title = {r.title: r.term_hits for r in corpus.records}
    assert by_title["Telework and productivity"] >= 2
    assert by_title["Cuisine tropicale"] == 0


def test_selection_ecarte_le_non_pertinent():
    """Un document sans recoupement de concept ou jugé peu pertinent n'est jamais retenu."""
    import dataclasses

    from literature_review_agent.core.config import Settings
    from literature_review_agent.pipeline import scoring_stage

    limits = dataclasses.replace(Settings().limits, max_documents=10, min_documents_useful=1)

    corpus = Corpus()
    corpus.add(_record(title="Telework and productivity", abstract="telework productivity",
                       doi="10.1/a", url="https://doi.org/10.1/a"))
    corpus.add(_record(title="Cuisine tropicale", abstract="recettes", doi="10.2/b",
                       url="https://doi.org/10.2/b"))
    corpus.add(_record(title="Autre travail à distance", abstract="télétravail et productivité",
                       doi="10.3/c", url="https://doi.org/10.3/c"))
    corpus.rank(["telework", "productivity", "télétravail"], ["en", "fr"])
    by_title = {r.title: r.doc_id for r in corpus.records}

    analyses = {
        by_title["Telework and productivity"]: {"relevance": 0.9},   # pertinent
        by_title["Cuisine tropicale"]: {"relevance": 0.95},          # hors sujet, score élevé
        by_title["Autre travail à distance"]: {"relevance": 0.1},    # concept recoupé, peu pertinent
    }
    scoring_stage.apply_analyses(corpus, analyses)
    retained, sufficiency, stats = scoring_stage.select_corpus(corpus, limits, analyses)

    titles = [r.title for r in retained]
    assert titles == ["Telework and productivity"]
    assert stats["rejected_no_concept_match"] == 1
    assert stats["rejected_low_relevance"] == 1
    assert stats["not_analysed_over_budget"] == 0
    # Les identifiants d'origine sont conservés (ils identifient le texte téléchargé et les
    # citations déjà produites) : la sélection ne renomme jamais les documents.
    assert [r.doc_id for r in retained] == [by_title["Telework and productivity"]]


def test_selection_ecarte_le_titre_en_double():
    """Même travail vu par deux fournisseurs (titre identique, DOI et auteurs distincts).

    Le dédoublonnage du collecteur compare titre ET auteurs : une prépublication et sa version
    publiée passent donc toutes les deux. Le corpus final contenait deux fois la même référence et
    le contrôle R7 refusait la sortie (constaté au test de chaîne réel).
    """
    import dataclasses

    from literature_review_agent.core.config import Settings
    from literature_review_agent.pipeline import scoring_stage

    limits = dataclasses.replace(Settings().limits, max_documents=10, min_documents_useful=1)
    titre = "Part-time or full-time teleworking? A systematic review"

    corpus = Corpus()
    corpus.add(_record(title=titre, abstract="teleworking productivity review",
                       doi="10.1/a", url="https://doi.org/10.1/a", authors=["Jane Doe"]))
    corpus.add(_record(title=titre.upper(), abstract="teleworking productivity review",
                       doi="10.2/b", url="https://doi.org/10.2/b", authors=["John Roe"],
                       provider="openalex"))
    corpus.rank(["teleworking", "productivity"], ["en"])
    by_doi = {r.doi: r.doc_id for r in corpus.records}
    assert len(by_doi) == 2  # les deux notices existent bien dans le corpus collecté

    analyses = {by_doi["10.1/a"]: {"relevance": 0.9}, by_doi["10.2/b"]: {"relevance": 0.8}}
    scoring_stage.apply_analyses(corpus, analyses)
    retained, _suff, stats = scoring_stage.select_corpus(corpus, limits, analyses)

    assert len(retained) == 1
    assert stats["rejected_duplicate_title"] == 1
    # La version la plus pertinente est conservée, avec son identifiant D'ORIGINE (jamais renommé).
    assert retained[0].doc_id == by_doi["10.1/a"]


def test_comptages_limites_aux_documents_retenus():
    """Régression : les répartitions portaient sur tout le corpus collecté (84) au lieu des
    documents réellement retenus (7), rendant les statistiques incohérentes."""
    corpus = Corpus()
    corpus.add(_record(title="A retenir", abstract="telework"))
    corpus.add(_record(title="B aussi", abstract="telework", doi="10.9/b",
                       url="https://doi.org/10.9/b"))
    corpus.rank(["telework"], ["en"])

    subset = corpus.records[:1]
    counts = corpus.counts(subset)
    assert sum(counts["by_language"].values()) == 1
    assert sum(counts["by_type"].values()) == 1
    assert sum(counts["by_geography"].values()) == 1

    complet = corpus.counts()
    assert sum(complet["by_language"].values()) == 2
