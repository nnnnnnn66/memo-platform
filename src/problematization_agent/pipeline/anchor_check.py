"""Contrôle d'ancrage déterministe (étape [8]) — le cœur anti-hallucination.

Une affirmation théorique n'est conservée que si son `doc_id` existe dans le corpus amont ET que sa
citation est un fragment verbatim du texte réellement disponible. Sinon elle est RETIRÉE (jamais
réparée) et le retrait est compté et déclaré.
"""

from ..schemas.statement import AnchoredStatement

# Libellés qui désignent le résumé (le modèle peut les écrire en français ou en anglais).
_ABSTRACT_LABELS = ("resume", "résumé", "abstract")


def _correct_section(statement: AnchoredStatement, index) -> None:
    """Remplace une localisation CONTREDITE par la source réellement mesurée.

    Le modèle déclare parfois une section (« resume ») qui ne correspond pas à l'endroit où la
    citation existe vraiment. On ne devine jamais une section précise : on ne corrige que la
    contradiction, en nommant la source effectivement vérifiée.
    """
    locate = getattr(index, "locate_quote", None)
    if not callable(locate):
        return
    where = locate(statement.doc_id, statement.quote)
    declared = (statement.section or "").strip().lower()
    is_abstract = any(label in declared for label in _ABSTRACT_LABELS)
    if where == "full_text" and (not declared or is_abstract):
        statement.section = "texte intégral"
    elif where == "abstract" and not is_abstract:
        statement.section = "résumé"
    elif where == "excerpt" and not declared:
        statement.section = "citation extraite (étape 3)"


def check_statements(statements, index, min_chars: int = 25,
                     allowed_ids: set[str] | None = None) -> tuple[list[AnchoredStatement], int]:
    """Retourne (affirmations ancrées, nombre retiré)."""
    kept: list[AnchoredStatement] = []
    removed = 0
    for statement in statements or []:
        doc_id = (statement.doc_id or "").strip()
        known = doc_id in index.doc_ids and (allowed_ids is None or doc_id in allowed_ids)
        if known and statement.quote.strip() and index.quote_ok(doc_id, statement.quote,
                                                               min_chars=min_chars):
            statement.anchored = True
            _correct_section(statement, index)
            kept.append(statement)
        else:
            removed += 1
    return kept, removed


def check_statement_list(container, fields: tuple[str, ...], index, min_chars: int = 25,
                         allowed_ids: set[str] | None = None) -> int:
    """Applique le contrôle aux champs d'affirmations d'un conteneur. Retourne le total retiré."""
    removed_total = 0
    for field in fields:
        kept, removed = check_statements(getattr(container, field, []) or [], index,
                                         min_chars=min_chars, allowed_ids=allowed_ids)
        setattr(container, field, kept)
        removed_total += removed
    return removed_total


def check_statements_and_report(obj, index, min_chars: int = 25) -> int:
    """Contrôle les affirmations d'une sortie de phase (objet à `.justification`)."""
    kept, removed = check_statements(getattr(obj.justification, "statements", []) or [], index,
                                     min_chars=min_chars)
    obj.justification.statements = kept
    return removed

