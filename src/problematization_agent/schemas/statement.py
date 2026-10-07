"""Affirmation ancrée : le cœur anti-hallucination de l'étape 4.

Une affirmation théorique n'existe que si elle porte un `doc_id` du corpus amont ET une citation
verbatim réellement présente dans le texte du document. `anchored` est posé par le pipeline
déterministe, jamais par le modèle.
"""

from pydantic import Field, model_validator

from .common import StrictModel


class AnchoredStatement(StrictModel):
    text: str = ""
    doc_id: str = ""
    quote: str = ""
    section: str = ""
    anchored: bool = False  # posé par le contrôle d'ancrage (pas par le modèle)

    @model_validator(mode="before")
    @classmethod
    def _coerce_bare_string(cls, value):
        """Tolérance de forme : une affirmation donnée comme simple chaîne devient un texte."""
        if isinstance(value, str):
            return {"text": value}
        return value

    def to_reference(self) -> str:
        return f"[{self.doc_id}]"

    def summary(self) -> str:
        quote = (self.quote or "")[:120]
        return f"{self.text} [{self.doc_id}] « {quote} »"


def to_statement_objects(items) -> list[AnchoredStatement]:
    """Normalise une liste hétérogène (dicts ou chaînes) en affirmations ancrées."""
    out: list[AnchoredStatement] = []
    for item in items or []:
        if isinstance(item, AnchoredStatement):
            out.append(item)
        elif isinstance(item, dict):
            out.append(AnchoredStatement.model_validate(item))
        elif isinstance(item, str) and item.strip():
            out.append(AnchoredStatement(text=item))
    return out


def statements_to_strings(items) -> list[str]:
    return [s.summary() if isinstance(s, AnchoredStatement) else str(s) for s in (items or [])]
