"""Règles déterministes des hypothèses de recherche (SPEC §7, §10).

Cœur de la neutralité ET de la distinction des notions : une hypothèse est une PROPOSITION À EXAMINER.
Elle n'est ni une question, ni un objectif, ni un fait déjà démontré. Elle n'exige pas une causalité
qui n'est pas établie. Ces contrôles sont CODÉS : en cas de doute, ils signalent — l'humain tranche.
"""

import re
import unicodedata

# Marqueurs de relation (une hypothèse porte sur une relation, une différence, une explication…).
RELATION_MARKERS = [
    "associe", "associee", "association", "influence", "effet", "varie", "variation", "difference",
    "differe", "lien", "lie", "correle", "correlation", "depend", "predi", "explique", "relation",
    "augmente", "diminue", "ameliore", "reduit", "favorise", "freine", "impacte", "determine",
    "plus", "moins", "superieur", "inferieur",
]

# Verbes de causalité : une cause ne peut être posée que si elle est établie ou justifiée (SPEC §9.3).
CAUSAL_MARKERS = [
    "provoque", "provoquee", "cause", "entraine", "est la cause", "a l'origine de", "genere",
    "produit", "induit", "occasionne", "determine", "rend", "conduit a", "modere",
]

# Tournures qui présentent une conclusion comme un FAIT (SPEC §10.C).
FACT_MARKERS = [
    r"\bil est d[ée]montr[ée] que\b", r"\bon sait que\b", r"\bil est prouv[ée] que\b",
    r"\bil est [ée]tabli que\b", r"\bnous avons d[ée]montr[ée]\b", r"\bil est bien connu que\b",
    r"\bcomme chacun sait\b", r"\bil est [ée]vident que\b",
]

# Verbes d'action des OBJECTIFS (reprise de l'agent 6) : une hypothèse ne s'ouvre pas par un objectif.
OBJECTIVE_VERBS = [
    "identifier", "decrire", "caracteriser", "analyser", "comparer", "examiner", "mesurer", "estimer",
    "comprendre", "explorer", "determiner", "evaluer", "expliquer", "interpreter", "etudier",
]

# Marqueurs d'interrogation : une hypothèse n'est pas une question.
_INTERROGATIVES = [r"\bpourquoi\b", r"\bcomment\b", r"\bcombien\b", r"\bquand\b", r"\bo[uù]\b",
                   r"\bqui\b", r"\bquel(?:le|s|les)?\b", r"\bqu'?est-?ce\b"]

_VERB_RE = re.compile(r"^[^a-zà-ÿ]*([a-zà-ÿ]+)")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", _normalize(text)))


def opening_verb(text: str) -> str:
    match = _VERB_RE.search((text or "").strip().lower())
    return _normalize(match.group(1)).strip() if match else ""


def looks_like_question(text: str) -> bool:
    if not text:
        return False
    if text.strip().endswith("?"):
        return True
    return any(re.search(pat, text, re.IGNORECASE) for pat in _INTERROGATIVES)


def looks_like_objective(text: str) -> bool:
    """Une hypothèse qui s'ouvre par un verbe d'objectif (« Analyser … ») est en fait un objectif."""
    verb = opening_verb(text)
    return bool(verb) and any(verb.startswith(v[:5]) for v in OBJECTIVE_VERBS if len(v) >= 5)


def presupposed_fact_hits(text: str) -> list[str]:
    return [pat for pat in FACT_MARKERS if re.search(pat, (text or "").lower())]


def causal_hits(text: str) -> list[str]:
    norm = _normalize(text)
    return [marker for marker in CAUSAL_MARKERS if re.search(rf"\b{re.escape(marker)}", norm)]


def has_relation_marker(text: str) -> bool:
    norm = _normalize(text)
    return any(re.search(rf"\b{re.escape(m)}", norm) for m in RELATION_MARKERS)


def is_examinable(text: str, required_data: list[str] | None = None) -> bool:
    """Une hypothèse est examinable si elle énonce une relation OU si l'on précise les données requises."""
    return has_relation_marker(text) or bool([d for d in (required_data or []) if str(d).strip()])


def is_too_short(text: str, min_tokens: int = 4) -> bool:
    return len(tokens(text)) < min_tokens


def duplicate_hypotheses(formulations: list[str]) -> list[tuple[int, int]]:
    """Hypothèses quasi identiques (mêmes mots-clés) — redondance à signaler."""
    from itertools import combinations

    pairs = []
    for (i, a), (j, b) in combinations(enumerate(formulations, start=1), 2):
        ta, tb = tokens(a), tokens(b)
        if ta and tb and len(ta & tb) / len(ta | tb) >= 0.7:
            pairs.append((i, j))
    return pairs


def causal_is_justified(verb: str, context_text: str) -> bool:
    """La causalité est-elle établie/justifiée par le contexte fourni ? (recouvrement lexical)."""
    if not verb:
        return False
    return verb in _normalize(context_text)
