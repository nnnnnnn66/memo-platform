"""Adaptateurs de fournisseurs, testés hors réseau sur des réponses enregistrées."""

import pytest
from probleme_helpers import FakeFetcher

from research_problem_agent.sources.adapters import (
    arxiv,
    crossref,
    datacite,
    datagouv,
    dataeuropa,
    doaj,
    europepmc,
    hal,
    openaire,
    openalex,
    pubmed,
    zenodo,
)

OPENALEX = {"results": [{
    "display_name": "Job Burnout",
    "doi": "https://doi.org/10.1146/annurev.psych.52.1.397",
    "publication_date": "2001-02-01",
    "id": "https://openalex.org/W1",
    "primary_location": {"source": {"display_name": "Annual Review of Psychology"}},
    "abstract_inverted_index": {"Job": [0], "burnout": [1], "matters": [2]},
}]}

CROSSREF = {"message": {"items": [{
    "title": ["Beautiful Burnout"],
    "DOI": "10.5040/9780571289523.00000002",
    "URL": "https://doi.org/10.5040/9780571289523.00000002",
    "container-title": ["Theatre Journal"],
    "issued": {"date-parts": [[2014, 3, 4]]},
    "abstract": "<jats:p>Un résumé</jats:p>",
}]}}

DOAJ = {"results": [{"bibjson": {
    "title": "Burnout and Resilience",
    "year": "2022",
    "identifier": [{"id": "10.3390/bs12110422", "type": "doi"}],
    "link": [{"content_type": "text/html", "type": "fulltext",
              "url": "https://www.mdpi.com/2076-328X/12/11/422"}],
    "journal": {"title": "Behavioral Sciences"},
    "abstract": "Burnout syndrome…",
}}]}

HAL = {"response": {"docs": [{
    "title_s": ["Du stress au burnout scolaire"],
    "uri_s": "https://hal.science/hal-01234567",
    "doiId_s": "10.1234/hal.2018",
    "producedDate_s": "2018-01-01",
    "abstract_s": ["Revue de la littérature"],
    "journalTitle_s": "Psychologie française",
}]}}

ARXIV = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Burnout in software teams</title>
    <published>2024-01-01T00:00:00Z</published>
    <summary>We study burnout.</summary>
    <link rel="alternate" href="http://arxiv.org/abs/2401.00001v1"/>
  </entry>
</feed>"""

DATACITE = {"data": [{"attributes": {
    "doi": "10.26263/amitos-5955",
    "url": "https://amitos.example/handle/1",
    "titles": [{"title": "Επαγγελματική εξουθένωση"}],
    "publicationYear": 2021,
    "publisher": "Université du Péloponnèse",
    "descriptions": [{"descriptionType": "Abstract", "description": "Résumé"}],
}}]}

EUROPEPMC = {"resultList": {"result": [{
    "title": "Burnout among pathoanatomists",
    "doi": "10.32687/0869-866x-2026-34-2-194-199",
    "pubYear": "2026",
    "journalTitle": "Problems of Social Hygiene",
    "abstractText": "The article considers…",
}]}}

ESEARCH = {"esearchresult": {"idlist": ["42839930"]}}
ESUMMARY = {"result": {"42839930": {
    "title": "Suicide probability among physicians",
    "pubdate": "2026",
    "fulljournalname": "Front Med (Lausanne)",
    "articleids": [{"idtype": "doi", "value": "10.3389/fmed.2026.1943490"}],
}}}

OPENAIRE = {"results": [{
    "mainTitle": "New Perspective on Job Burnout",
    "publicationDate": "2012-06-01",
    "publisher": "SAGE Publications",
    "container": {"name": "Psychological Reports"},
    "pids": [{"scheme": "doi", "value": "10.2466/01.09.13.pr0.110.3.801-819"}],
    "instances": [{"urls": ["https://doi.org/10.2466/01.09.13.pr0.110.3.801-819"]}],
    "descriptions": ["<jats:p>Previous studies of job burnout…"],
}]}

ZENODO = {"hits": {"hits": [{
    "id": 14493392,
    "doi": "10.5281/zenodo.14493392",
    "links": {"self_html": "https://zenodo.org/records/14493392"},
    "metadata": {"title": "Dataset on burnout", "publication_date": "2024-12-15",
                 "publisher": "Zenodo", "description": "Anonymised survey data"},
}]}}

DATAGOUV = {"data": [{
    "title": "Population étrangère : chômage",
    "page": "https://www.data.gouv.fr/datasets/2013-population-etrangere-chomage",
    "created_at": "2014-05-07T12:00:00",
    "organization": {"name": "Ministère de l'intérieur"},
    "description": "Série statistique",
}]}

DATAEUROPA = {"result": {"results": [{
    "title": {"fr": "Demandes émotionnelles et épuisement", "en": "Emotional demands and burnout"},
    "description": {"en": "Survey data from a research project"},
    "resource": "http://data.europa.eu/88u/dataset/xyz",
    "issued": "2025-12-19T15:29:36.509020Z",
    "publisher": {"name": "Högskolan i Gävle"},
}]}}


CASES = [
    (openalex, {"works": OPENALEX}, {"source": "Annual Review of Psychology",
                                     "url": "https://doi.org/10.1146/annurev.psych.52.1.397",
                                     "doi": "10.1146/annurev.psych.52.1.397",
                                     "publication_date": "2001-02-01"}),
    (crossref, {"works": CROSSREF}, {"source": "Theatre Journal", "doi": "10.5040/9780571289523.00000002",
                                     "publication_date": "2014-03-04"}),
    (doaj, {"doaj.org": DOAJ}, {"doi": "10.3390/bs12110422", "publication_date": "2022",
                                "url": "https://www.mdpi.com/2076-328X/12/11/422"}),
    (hal, {"archives-ouvertes": HAL}, {"source": "Psychologie française",
                                       "url": "https://hal.science/hal-01234567",
                                       "doi": "10.1234/hal.2018"}),
    (arxiv, {"arxiv": ARXIV}, {"url": "http://arxiv.org/abs/2401.00001v1",
                               "publication_date": "2024-01-01"}),
    (datacite, {"datacite": DATACITE}, {"doi": "10.26263/amitos-5955",
                                        "source": "Université du Péloponnèse"}),
    (europepmc, {"ebi.ac.uk": EUROPEPMC}, {"doi": "10.32687/0869-866x-2026-34-2-194-199",
                                           "publication_date": "2026"}),
    (pubmed, {"esearch": ESEARCH, "esummary": ESUMMARY},
     {"doi": "10.3389/fmed.2026.1943490", "source": "Front Med (Lausanne)"}),
    (openaire, {"openaire": OPENAIRE}, {"doi": "10.2466/01.09.13.pr0.110.3.801-819",
                                        "source": "Psychological Reports"}),
    (zenodo, {"zenodo": ZENODO}, {"doi": "10.5281/zenodo.14493392", "source": "Zenodo"}),
    (datagouv, {"data.gouv.fr": DATAGOUV}, {"source": "Ministère de l'intérieur",
                                            "url": "https://www.data.gouv.fr/datasets/2013-population-etrangere-chomage"}),
    (dataeuropa, {"data.europa.eu": DATAEUROPA}, {"source": "Högskolan i Gävle",
                                                  "url": "http://data.europa.eu/88u/dataset/xyz"}),
]


@pytest.mark.parametrize("module,responses,attendu", CASES,
                         ids=[c[0].PROVIDER_ID for c in CASES])
def test_adaptateur_normalise_la_reponse(module, responses, attendu):
    fetcher = FakeFetcher(responses)

    records = module.search(fetcher, "burnout", 1)

    assert len(records) == 1, f"{module.PROVIDER_ID} doit retourner un enregistrement"
    record = records[0]
    assert record["title"], "le titre ne doit pas être vide"
    for key, value in attendu.items():
        assert record.get(key) == value, f"{module.PROVIDER_ID}.{key} = {record.get(key)!r}"


def test_openalex_reconstruit_le_resume():
    fetcher = FakeFetcher({"works": OPENALEX})
    record = openalex.search(fetcher, "burnout", 1)[0]
    assert record["snippet"] == "Job burnout matters"


def test_crossref_nettoie_le_html_du_resume():
    fetcher = FakeFetcher({"works": CROSSREF})
    record = crossref.search(fetcher, "burnout", 1)[0]
    assert record["snippet"] == "Un résumé"


def test_openaire_retire_les_balises_jats():
    fetcher = FakeFetcher({"openaire": OPENAIRE})
    record = openaire.search(fetcher, "burnout", 1)[0]
    assert "<jats:p>" not in record["snippet"]
    assert record["snippet"].startswith("Previous studies")


def test_adapter_renvoie_une_liste_vide_si_aucun_resultat():
    fetcher = FakeFetcher({"works": {"results": []}})
    assert openalex.search(fetcher, "rien", 5) == []
