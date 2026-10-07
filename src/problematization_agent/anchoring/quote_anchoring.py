"""Ancrage verbatim : normalisation tolérante et contrôle de présence littérale.

Reprend la leçon de l'étape 3 : le contrôle ne doit JAMAIS accepter par défaut. Une citation courte
(25–60 caractères) introuvable littéralement est rejetée (l'ancienne boucle `range(0, len(q)-60, 200)`
étant vide, elle faisait « fail-open »).
"""

from ..core.security_rules import normalize_for_quote, quote_is_anchored

is_quote_anchored = quote_is_anchored

__all__ = ["normalize_for_quote", "quote_is_anchored", "is_quote_anchored"]
