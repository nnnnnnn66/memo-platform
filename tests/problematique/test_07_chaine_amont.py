"""Passation amont : la VRAIE sortie de l'agent 3 doit être consommable telle quelle.

Régression constatée sur une sortie réelle (8 documents) : l'agent 3 place ses documents sous
`corpus.documents`, alors que ce contrat les attendait à la racine. Résultat : l'agent 4 recevait
un corpus VIDE et répondait « corpus vide » au lieu de travailler — la chaîne cassait à la
passation 3 → 4, sans qu'aucun test unitaire ne le voie (chaque agent était testé avec un payload
fabriqué à la main, jamais avec la sortie réelle du précédent).
"""

from problematization_agent.schemas.input import ProblemRequest


def _sortie_agent3(n: int = 2) -> dict:
    """Reproduit la STRUCTURE de la sortie réelle de l'agent 3 (documents sous `corpus`)."""
    documents = [
        {
            "doc_id": f"D{i}",
            "title": f"Étude {i} sur le télétravail",
            "authors": ["Awa Traoré"],
            "year": 2023,
            "venue": "Revue africaine de gestion",
            "doi": f"10.1234/rag.2023.00{i}",
            "url": f"https://doi.org/10.1234/rag.2023.00{i}",
            "abstract": "Le télétravail partiel modifie la coordination des équipes.",
            "document_type": "article",
            "language": "fr",
            "findings": [],
            "limits": [],
            "full_text": {"downloaded": False, "text_layer": False},
        }
        for i in range(1, n + 1)
    ]
    return {
        "agent": "literature_review_agent",
        "version": "1.0",
        "status": "ready_for_verification",
        "corpus": {"documents": documents, "documents_count": n},
        "diagnosis": {"matrix_row_id": "test_hypothesis",
                      "reasoning_logic": "hypothetico_deductive"},
        "validation": {"verified": True, "verifier_status": "verified"},
    }


def test_sortie_agent3_nidifiee_est_consommee_telle_quelle():
    request = ProblemRequest(student_id="s", subject_text="sujet",
                             upstream_literature=_sortie_agent3(3))

    assert len(request.corpus_documents()) == 3
    assert request.upstream_literature.is_verified is True


def test_documents_a_la_racine_toujours_acceptes():
    """L'ancienne forme (documents à la racine) ne doit pas régresser."""
    payload = _sortie_agent3(2)
    payload["documents"] = payload.pop("corpus")["documents"]

    request = ProblemRequest(student_id="s", subject_text="sujet", upstream_literature=payload)

    assert len(request.corpus_documents()) == 2


def test_corpus_nidifie_aboutit_a_un_index_non_vide():
    """Le vrai enjeu : l'agent 4 doit pouvoir indexer le texte de ces documents."""
    import dataclasses

    from problematization_agent.core.config import Settings
    from problematization_agent.pipeline import corpus_loader

    request = ProblemRequest(student_id="s", subject_text="sujet",
                             upstream_literature=_sortie_agent3(3))
    index = corpus_loader.load(request, dataclasses.replace(Settings().limits))

    assert len(index.documents) == 3
