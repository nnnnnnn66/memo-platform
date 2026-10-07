"""Chargement et indexation du corpus amont (étape [5]) — déterministe, sans LLM.

Construit l'index d'ancrage : par `doc_id`, tout le texte réellement disponible (texte intégral
fourni ou lu sur disque, résumé, citations verbatim de l'étape 3). Les `doc_id` sont repris TELS
QUELS : jamais renumérotés.
"""

from ..anchoring import CorpusIndex


def load(request, limits) -> CorpusIndex:
    documents = request.corpus_documents()
    return CorpusIndex(
        documents,
        document_texts=request.document_texts,
        documents_dir=request.documents_dir or None,
        max_documents=int(getattr(limits, "max_documents_read", 60)),
        max_document_chars=int(getattr(limits, "max_document_chars", 80000)),
    )
