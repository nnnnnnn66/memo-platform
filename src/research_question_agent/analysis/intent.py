"""Intentions de recherche : enum canonique + normalisation (SPEC §7).

L'intention dit CE QUE la recherche cherche à faire (décrire, comprendre, expliquer, comparer…).
Elle ne doit JAMAIS être confondue avec une approche méthodologique ou une logique de raisonnement.
"""

import re
import unicodedata

# Enum canonique (ordre = ordre de la SPEC, plus « autre »).
INTENTS = [
    "decrire",
    "comprendre",
    "explorer",
    "expliquer",
    "comparer",
    "mesurer",
    "evaluer",
    "examiner_evolution",
    "identifier_facteurs",
    "autre",
]

LABELS = {
    "decrire": "décrire un phénomène",
    "comprendre": "comprendre une expérience ou un processus",
    "explorer": "explorer un phénomène peu étudié",
    "expliquer": "expliquer un phénomène",
    "comparer": "comparer des situations",
    "mesurer": "mesurer une relation",
    "evaluer": "évaluer une intervention",
    "examiner_evolution": "examiner une évolution",
    "identifier_facteurs": "identifier des facteurs associés à un phénomène",
    "autre": "autre intention (à préciser)",
}

# Alias tolérants (le modèle écrit parfois une phrase ou une variante).
_ALIASES = {
    "decrire": "decrire", "description": "decrire", "descriptif": "decrire", "describe": "decrire",
    "comprendre": "comprendre", "comprehension": "comprendre", "understand": "comprendre",
    "explorer": "explorer", "exploratoire": "explorer", "explore": "explorer",
    "expliquer": "expliquer", "explication": "expliquer", "explain": "expliquer",
    "comparer": "comparer", "comparaison": "comparer", "compare": "comparer",
    "mesurer": "mesurer", "mesure": "mesurer", "measure": "mesurer",
    "evaluer": "evaluer", "evaluation": "evaluer", "evaluate": "evaluer",
    "examiner_evolution": "examiner_evolution", "evolution": "examiner_evolution",
    "examiner l'evolution": "examiner_evolution", "examiner l evolution": "examiner_evolution",
    "identifier_facteurs": "identifier_facteurs", "facteurs": "identifier_facteurs",
    "identifier les facteurs": "identifier_facteurs", "facteurs associes": "identifier_facteurs",
    "autre": "autre", "other": "autre",
}


def _key(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^a-z_ ]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def normalize_intent(value: str) -> str:
    """Ramène une valeur libre à une clé de l'enum canonique, sinon « autre »."""
    key = _key(value)
    if not key:
        return "autre"
    if key in INTENTS:
        return key
    if key in _ALIASES:
        return _ALIASES[key]
    # Recherche par mot : le modèle peut renvoyer une phrase.
    for token in key.split(" "):
        if token in INTENTS:
            return token
        if token in _ALIASES and _ALIASES[token]:
            return _ALIASES[token]
    return "autre"


def is_known(value: str) -> bool:
    return normalize_intent(value) in INTENTS
