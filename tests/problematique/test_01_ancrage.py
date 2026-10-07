"""Ancrage verbatim : la citation doit exister littéralement dans le texte réel."""

from problematique_helpers import (
    DOC_A,
    INVENTED_QUOTE,
    QUOTE_A,
    StubLLM,
)

from problematization_agent.anchoring import CorpusIndex, quote_is_anchored
from problematization_agent.pipeline import campaign
from problematization_agent.schemas.output import ProblemStatus


def test_citation_courte_inventee_rejetee():
    """Bug « fail-open » de l'étape 3 : une citation inventée de 25 à 60 caractères doit être
    REJETÉE, jamais acceptée par défaut."""
    assert 25 <= len(INVENTED_QUOTE) <= 60
    assert quote_is_anchored(INVENTED_QUOTE, DOC_A["abstract"]) is False


def test_citation_reelle_acceptee():
    assert quote_is_anchored(QUOTE_A, DOC_A["abstract"]) is True


def test_citation_longue_partiellement_presente_refusee():
    quote = ("le télétravail augmente la productivité des développeurs de 12 % dans les "
             "entreprises d'Abidjan et cette phrase n'existe pas dans le texte source relu")
    assert quote_is_anchored(quote, DOC_A["abstract"]) is False


def test_citation_trop_courte_rejetee():
    assert quote_is_anchored("télétravail", DOC_A["abstract"]) is False


class _RawDoc:
    def __init__(self, payload: dict):
        self.__dict__.update(payload)
        self.findings = payload.get("findings", [])
        self.limits = payload.get("limits", [])


def test_index_portees_et_ancrage():
    index = CorpusIndex([_RawDoc(DOC_A)])
    assert index.scope("D1") == "abstract_only"
    assert index.quote_ok("D1", QUOTE_A) is True
    assert index.quote_ok("D1", INVENTED_QUOTE) is False
    assert index.quote_ok("INCONNU", QUOTE_A) is False


def test_index_document_sans_texte():
    index = CorpusIndex([_RawDoc({"doc_id": "D9", "title": "sans texte"})])
    assert index.scope("D9") == "absent"
    assert index.quote_ok("D9", QUOTE_A) is False


def test_localisation_de_la_citation_est_mesuree():
    """`locate_quote` dit OÙ la citation existe réellement (texte intégral vs résumé)."""
    index = CorpusIndex([_RawDoc(DOC_A)], document_texts={"D1": "Introduction. " + QUOTE_A})
    assert index.locate_quote("D1", QUOTE_A) == "full_text"
    assert index.locate_quote("D1", INVENTED_QUOTE) == ""

    sans_texte = CorpusIndex([_RawDoc(DOC_A)])
    assert sans_texte.locate_quote("D1", QUOTE_A) == "abstract"


def test_section_contredite_remplacee_par_la_source_reelle():
    """Citation du texte intégral annoncée « resume » = localisation contredite -> corrigée.

    Régression constatée en exécution réelle (contrôle L1 du vérificateur) : le modèle
    déclarait une section qui ne correspondait pas à l'endroit où la citation existait.
    """
    from problematization_agent.pipeline import anchor_check
    from problematization_agent.schemas.statement import AnchoredStatement

    index = CorpusIndex([_RawDoc(DOC_A)], document_texts={"D1": "Introduction. " + QUOTE_A})
    statement = AnchoredStatement(text="affirmation", doc_id="D1", quote=QUOTE_A, section="resume")

    kept, removed = anchor_check.check_statements([statement], index)

    assert removed == 0
    assert kept[0].section == "texte intégral"


def test_section_du_resume_conservee_quand_elle_est_exacte():
    from problematization_agent.pipeline import anchor_check
    from problematization_agent.schemas.statement import AnchoredStatement

    index = CorpusIndex([_RawDoc(DOC_A)])   # seul le résumé est disponible
    statement = AnchoredStatement(text="affirmation", doc_id="D1", quote=QUOTE_A, section="resume")

    kept, _ = anchor_check.check_statements([statement], index)

    assert kept[0].section == "resume"


def test_campagne_retire_les_citations_inventees(settings, request_factory):
    """Le modèle invente ses citations : elles sont retirées, et la note est bloquée faute de
    fondement ancré (jamais transmise au vérificateur)."""
    result = campaign.run(request_factory(), settings, StubLLM(quote_mode="invented"),
                          allow_network=False)

    assert result.statements_removed >= 1
    assert result.output.status == ProblemStatus.blocked
    assert result.output.evidence.statements_anchored == 0
    assert result.verifier_status == "pending"
    assert any("ancrage verbatim" in note for note in result.output.limits_of_this_note)
    for statement in result.output.gap.statements:
        assert statement.anchored is False
    for note in result.output.limits_of_this_note:
        assert "affirmations produites ont été retirées" not in note or True
