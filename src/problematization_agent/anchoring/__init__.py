"""Ancrage verbatim : index du corpus amont et contrôle des citations.

Cœur anti-hallucination de l'étape 4. Aucune citation n'est « réparée » : une citation qui n'existe
pas littéralement dans le texte du document cité est RETIRÉE.
"""

from .index import CorpusIndex, SourceDocument
from .quote_anchoring import is_quote_anchored, normalize_for_quote, quote_is_anchored

__all__ = [
    "CorpusIndex",
    "SourceDocument",
    "is_quote_anchored",
    "normalize_for_quote",
    "quote_is_anchored",
]
