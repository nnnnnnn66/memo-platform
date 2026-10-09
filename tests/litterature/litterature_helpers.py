"""Aides de test de l'Agent Revue de littérature (aucun réseau, aucun coût)."""

import json

# --- réponses simulées des phases LLM ---------------------------------------------------------

KEYWORDS = {
    "agent": "literature_review_agent",
    "version": "1.0",
    "subject_reference": {
        "original": "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024",
        "reformulated": "",
    },
    "concepts": [
        {"concept": "télétravail", "keywords_fr": ["télétravail", "travail à distance"],
         "keywords_en": ["telework", "remote work"], "synonyms": ["travail hybride"],
         "variants": ["teletravail"]},
        {"concept": "productivité", "keywords_fr": ["productivité"], "keywords_en": ["productivity"],
         "synonyms": ["performance"], "variants": []},
    ],
    "strategy": {
        "combinations": ["télétravail AND productivité", "telework AND productivity"],
        "document_types": ["article", "thesis"], "period": "2020-2024", "languages": ["fr", "en"],
        "selection_criteria": ["revu par les pairs", "terrain africain privilégié"],
        "cascade_justification": "sujet ivoirien : la cascade commence par la Côte d'Ivoire",
    },
    "queries": [
        {"query": "télétravail productivité", "concepts": ["télétravail", "productivité"],
         "kind": "publications", "scope": "international", "language": "fr",
         "rationale": "littérature francophone sur le lien direct"},
        {"query": "telework productivity", "concepts": ["télétravail", "productivité"],
         "kind": "publications", "scope": "international", "language": "en",
         "rationale": "littérature internationale"},
        {"query": "télétravail Côte d'Ivoire", "concepts": ["télétravail"],
         "kind": "theses", "scope": "ivory_coast", "language": "fr",
         "rationale": "travaux ivoiriens"},
    ],
    "subject_is_too_broad": False,
    "clarification_questions": [],
    "confidence": {"overall": 0.7, "rationale": "cadre précis"},
}

KEYWORDS_TOO_BROAD = {
    **KEYWORDS,
    "subject_is_too_broad": True,
    "queries": [],
    "clarification_questions": ["Quel phénomène précis du sport ?", "Quelle population ?"],
}


def batch(docs: list[dict]) -> dict:
    """Lot d'analyses P2 : `docs` = [{doc_id, quote, relevance, scope}]."""
    documents = []
    for item in docs:
        documents.append({
            "doc_id": item["doc_id"],
            "relevance": item.get("relevance", 0.8),
            "theme": item.get("theme", "télétravail et productivité"),
            "method": item.get("method", "enquête par questionnaire"),
            "field_site": item.get("field_site", "entreprises de services numériques"),
            "extraction_scope": item.get("scope", "abstract_only"),
            "findings": [{"claim": item.get("claim", "Effet mesuré sur la productivité"),
                          "quote": item.get("quote", ""),
                          "locator_section": "results", "locator_page": 1}]
            if item.get("quote") is not None else [],
            "limits": [{"claim": item.get("limit", "échantillon restreint"),
                        "quote": item.get("limit_quote", ""),
                        "locator_section": "limits", "locator_page": 1}]
            if item.get("limit_quote") is not None else [],
        })
    return {"agent": "literature_review_agent", "version": "1.0", "documents": documents}


def synthesis(doc_ids: list[str], **overrides) -> dict:
    out = {
        "agent": "literature_review_agent",
        "version": "1.0",
        "comparison": {
            "themes": [{
                "theme": "effets du télétravail sur la productivité",
                "doc_ids": doc_ids,
                "convergences": ["Plusieurs travaux mesurent un effet positif modéré"],
                "divergences": ["Ampleur variable selon les contextes"],
                "limits": ["échantillons non représentatifs"],
                "gaps": ["aucune donnée ivoirienne"],
            }],
            "methods_used": ["enquête par questionnaire"],
            "results_summary": ["effet globalement positif mais hétérogène"],
        },
        "synthesis": {
            "state_of_knowledge": "La littérature documente un effet globalement positif du "
                                  "télétravail sur la productivité, variable selon les contextes.",
            "authors_and_schools": ["économie du travail"],
            "open_questions": ["l'effet tient-il dans un contexte ivoirien ?"],
            "blind_spots": ["aucun terrain subsaharien"],
            "caution_notes": ["sources majoritairement européennes"],
        },
        "unknowns": ["ampleur exacte à Abidjan"],
        "limits_of_this_review": ["corpus majoritairement anglophone"],
    }
    out.update(overrides)
    return out


DIAGNOSIS = {
    "agent": "literature_review_agent",
    "version": "1.0",
    "diagnosis": {
        "matrix_row_id": "test_hypothesis",
        "matrix_row_label": "Tester une hypothèse",
        "semantic_indicators": ["quel est l'impact de X sur Y"],
        "reasoning_logic": "hypothetico_deductive",
        "research_type": "explanatory",
        "approach": "quantitative",
        "techniques": ["questionnaire fermé", "régressions"],
        "justification": "le sujet interroge un effet mesurable du télétravail sur la productivité",
        "alternatives": ["démarche mixte si l'accès quantitatif est limité"],
        "alignment_alerts": [],
        "evidence_from_corpus": "méthodes quantitatives dominantes dans le corpus",
        "missing_to_decide": ["accès aux données internes d'entreprise"],
        "status": "proposal_to_validate_with_student",
        "confidence": {"overall": 0.6, "rationale": "corpus cohérent, terrain peu documenté"},
    },
}

VERIFIER_VERIFIED = {
    "agent": "literature_review_verifier", "version": "1.0", "verdict": "verified",
    "controls": [{"code": "L1", "resultat": "ok", "detail": ""}], "corrections": [], "flags": [],
}

VERIFIER_CORRECTIONS = {
    "agent": "literature_review_verifier", "version": "1.0",
    "verdict": "corrections_requested",
    "controls": [{"code": "L9", "resultat": "echec", "detail": "limites absentes"}],
    "corrections": ["L9: préciser les limites du corpus"], "flags": [],
}


class StubLLM:
    """LLM simulé : file de réponses prédéfinies."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.sent = []

    def complete(self, system, user):
        self.sent.append({"system": system, "user": user})
        if not self.responses:
            raise AssertionError("StubLLM: plus de réponses disponibles")
        self.calls += 1
        return self.responses.pop(0)


# --- faux fournisseurs réseau ------------------------------------------------------------------

ABSTRACT_A = ("Cette étude mesure l'effet du télétravail sur la productivité des salariés. "
              "Les résultats montrent une hausse de la productivité de 4 % sur un an, avec une "
              "grande hétérogénéité entre les métiers.")
ABSTRACT_B = ("Nous analysons le télétravail partiel et la performance des équipes logicielles. "
              "L'effet estimé est positif mais faible et dépend fortement de l'organisation.")


def openalex_payload():
    return {"results": [
        {"display_name": "Telework and productivity: evidence", "doi": "https://doi.org/10.1/a",
         "publication_date": "2021-05-01", "id": "https://openalex.org/W1", "type": "article",
         "language": "en", "authorships": [{"author": {"display_name": "Jane Doe"}}],
         "primary_location": {"source": {"display_name": "Journal of Work"},
                             "pdf_url": "https://repository.example/a.pdf"},
         "best_oa_location": {"pdf_url": "https://repository.example/a.pdf", "license": "cc-by",
                              "host_type": "repository"},
         "open_access": {"is_oa": True},
         "biblio": {"volume": "12", "issue": "3", "first_page": "45", "last_page": "67"},
         "abstract_inverted_index": {"Telework": [0], "raises": [1], "productivity": [2]}},
        {"display_name": "Telework and productivity: evidence",   # doublon (même DOI)
         "doi": "https://doi.org/10.1/a", "publication_date": "2021-05-01",
         "id": "https://openalex.org/W1", "type": "article", "authorships": [],
         "primary_location": {}, "open_access": {"is_oa": True}},
    ]}


def crossref_payload():
    return {"message": {"items": [
        {"title": ["Télétravail et performance des équipes"], "DOI": "10.2/b",
         "URL": "https://doi.org/10.2/b", "container-title": ["Revue du travail"],
         "issued": {"date-parts": [[2022, 6, 1]]}, "type": "journal-article",
         "language": "fr", "author": [{"given": "Marie", "family": "Dupont"}],
         "volume": "8", "issue": "2", "page": "10-30",
         "abstract": ABSTRACT_B, "link": [{"URL": "https://publisher.example/b.pdf",
                                          "content-type": "application/pdf"}]},
    ]}}


def hal_payload():
    return {"response": {"docs": [
        {"title_s": ["Le télétravail à Abidjan : premières observations"],
         "authFullName_s": ["Kouassi Yao"], "producedDate_s": "2023",
         "journalTitle_s": "Cahiers ivoiriens de gestion", "doiId_s": "10.3/c",
         "uri_s": "https://hal.science/hal-00000001", "language_s": ["fr"],
         "abstract_s": ["Étude exploratoire menée en Côte d'Ivoire sur le télétravail."],
         "fileMain_s": "https://hal.science/hal-00000001/document", "docType_s": "ART"},
    ]}}


def theses_fr_payload():
    return {"theses": [
        {"titrePrincipal": "Télétravail et productivité dans les entreprises ivoiriennes",
         "auteurs": [{"nom": "Traoré", "prenom": "Awa"}], "dateSoutenance": "12/05/2025",
         "etabSoutenanceN": "Université de Rennes", "discipline": "Sciences de gestion",
         "nnt": "2025URENG002", "doi": "", "resume": None},
    ]}


def unpaywall_payload():
    return {"is_oa": True, "oa_status": "green",
            "best_oa_location": {"url_for_pdf": "https://repository.example/a.pdf",
                                 "host_type": "repository", "license": "cc-by"},
            "oa_locations": [{"url_for_pdf": "https://repository.example/a.pdf",
                              "host_type": "repository", "license": "cc-by"},
                             {"url": "https://hal.science/hal-9999/document",
                              "host_type": "repository", "license": "cc-by"}]}


class FakeApiFetcher:
    """Client API simulé : réponses enregistrées par fragment d'URL, aucun appel réseau."""

    def __init__(self, responses: dict, polite_email: str = "test@example.org"):
        self.responses = responses
        self.cfg = {"polite_email": polite_email, "user_agent": "test"}
        self.requests = 0
        self.bytes_downloaded = 0
        self.errors = []
        self.seen: list[str] = []

    def _payload(self, url: str):
        for fragment, payload in self.responses.items():
            if fragment in url:
                return payload
        raise AssertionError(f"FakeApiFetcher : aucune réponse pour {url}")

    def fetch(self, url: str, params=None, cost: int = 1, headers: dict | None = None) -> str:
        payload = self._payload(url)
        self.requests += cost
        self.seen.append(url)
        self.last_headers = dict(headers or {})
        return payload if isinstance(payload, str) else json.dumps(payload)

    def fetch_json(self, url: str, params=None, cost: int = 1,
                   headers: dict | None = None) -> dict:
        payload = self._payload(url)
        self.requests += cost
        self.seen.append(url)
        self.last_headers = dict(headers or {})
        return json.loads(payload) if isinstance(payload, str) else payload


DEFAULT_RESPONSES = {
    "api.openalex.org/works": openalex_payload(),
    "api.crossref.org/works": crossref_payload(),
    "api.archives-ouvertes.fr": hal_payload(),
    "theses.fr": theses_fr_payload(),
    "api.unpaywall.org": unpaywall_payload(),
    "api.datacite.org": {"data": []},
    "zenodo.org": {"hits": {"hits": []}},
    "api.openaire.eu": {"results": []},
    "export.arxiv.org": "<feed xmlns='http://www.w3.org/2005/Atom'></feed>",
    "api.osf.io": {"data": []},
    "doaj.org": {"results": []},
    "ebi.ac.uk": {"resultList": {"result": []}},
    "eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch": {"esearchresult": {"idlist": []}},
    "data.gouv.fr": {"data": []},
    "data.europa.eu": {"result": {"results": []}},
}


class FakeDownloader:
    """Téléchargeur simulé : renvoie des octets prédéfinis, ou refuse."""

    def __init__(self, payloads: dict | None = None, default: bytes | None = None):
        self.payloads = payloads or {}
        self.default = default
        self.downloads = 0
        self.bytes_downloaded = 0
        self.errors = []
        self.attempted: list[str] = []

    def download_pdf(self, url: str) -> bytes:
        from literature_review_agent.core.errors import ErrorState, PipelineError

        self.attempted.append(url)
        if url in self.payloads:
            data = self.payloads[url]
            self.downloads += 1
            self.bytes_downloaded += len(data)
            return data
        if self.default is not None:
            self.downloads += 1
            self.bytes_downloaded += len(self.default)
            return self.default
        raise PipelineError(ErrorState.TOOL_ERROR, "HTTP 403 (téléchargement)")


def as_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


class SmartStubLLM:
    """LLM simulé qui répond selon la phase détectée dans le prompt système.

    Il lit les `doc_id` et les résumés réellement présents dans le message : les citations produites
    sont donc de vraies citations du texte fourni — ce qui permet de tester l'ancrage verbatim sans
    modèle réel.
    """

    def __init__(self, keywords: dict | None = None,
                 verifier: dict | list[dict] | None = None,
                 diagnosis: dict | None = None, with_fake_quote: bool = False):
        self.keywords = keywords or KEYWORDS
        self.verifier = verifier or VERIFIER_VERIFIED
        self.diagnosis = diagnosis or DIAGNOSIS
        self.with_fake_quote = with_fake_quote
        self.calls = 0
        self.verifier_calls = 0
        self.sent = []

    # --- helpers ---
    @staticmethod
    def _doc_ids(user: str) -> list[str]:
        found: list[str] = []
        for match in re.finditer(r"\[(D\d+)\]", user):
            if match.group(1) not in found:
                found.append(match.group(1))
        return found

    @staticmethod
    def _abstracts(user: str) -> dict[str, str]:
        """Associe chaque doc_id au texte disponible dans le message (résumé ou passage lu)."""
        out: dict[str, str] = {}
        blocks = re.split(r"\n\[(D\d+)\]", user)
        for index in range(1, len(blocks) - 1, 2):
            doc_id, body = blocks[index], blocks[index + 1]
            out[doc_id] = body
        return out

    @staticmethod
    def _quote(body: str) -> str:
        """Choisit une citation réellement présente dans le résumé du bloc (sans étiquette)."""
        for pattern in (r"(?m)^R[ée]sum[ée]\s*:\s*(.+)$", r"(?m)^(?:Texte|Passage)[^\n:]*:\s*(.+)$"):
            for match in re.finditer(pattern, body):
                text = match.group(1).strip()
                for sentence in re.split(r"(?<=[.!?])\s+", text):
                    sentence = sentence.strip()
                    if 40 <= len(sentence) <= 400:
                        return sentence[:400]
        return ""

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        self.sent.append({"system": system, "user": user})
        directive = system.lower()
        # L'ordre compte : le prompt du vérificateur mentionne aussi la synthèse et les
        # comparaisons, il doit donc être testé en premier.
        if "vérificateur" in directive:
            # `verifier` peut être un verdict unique ou une SÉQUENCE de verdicts : la séquence
            # permet de tester la boucle de vérification (corrections… puis verdict final).
            if isinstance(self.verifier, list):
                index = min(self.verifier_calls, len(self.verifier) - 1)
                self.verifier_calls += 1
                return as_json(self.verifier[index])
            return as_json(self.verifier)
        if "concepts, mots-clés et stratégie" in directive:
            return as_json(self.keywords)
        if "noter et analyser un lot" in directive:
            ids = self._doc_ids(user)
            bodies = self._abstracts(user)
            docs = []
            for doc_id in ids:
                body = bodies.get(doc_id, "")
                quote = self._quote(body) if body else ""
                if self.with_fake_quote:
                    quote = ("Les auteurs démontrent une hausse de 42 % de la productivité en "
                             "Côte d'Ivoire entre 1998 et 2001.")
                scope = "abstract_only" if body else "metadata_only"
                entry = {"doc_id": doc_id, "relevance": 0.7, "theme": "télétravail et productivité",
                         "method": "enquête par questionnaire", "field_site": "entreprises",
                         "extraction_scope": scope, "findings": [], "limits": []}
                if quote:
                    entry["findings"] = [{"claim": "Effet mesuré sur la productivité", "quote": quote,
                                          "locator_section": "results", "locator_page": 1}]
                docs.append(entry)
            return as_json({"agent": "literature_review_agent", "version": "1.0",
                            "documents": docs})
        if "synthèse critique" in directive or "comparaison" in directive:
            return as_json(synthesis(self._doc_ids(user)))
        if "diagnostic méthodologique" in directive:
            return as_json(self.diagnosis)
        raise AssertionError(f"SmartStubLLM : phase inconnue (system={system[:80]!r})")


import re  # noqa: E402  (utilisé par SmartStubLLM)
