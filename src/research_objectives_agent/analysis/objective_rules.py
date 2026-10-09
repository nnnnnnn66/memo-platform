"""Règles déterministes des objectifs de recherche (SPEC §7.B, §7.C, §10).

Cœur de la neutralité ET de la distinction des notions : un objectif qui « démontre » présuppose un
résultat ; un objectif qui recopie une hypothèse n'est pas un objectif ; « lire des articles » est une
activité, pas un objectif scientifique. Ces contrôles sont CODÉS (pas seulement demandés au modèle) :
en cas de doute, ils signalent — l'humain tranche.
"""

import re
import unicodedata

# --- verbes d'action adaptés (SPEC §7.B) ---------------------------------------------------------
ACTION_VERBS = [
    "identifier", "decrire", "caracteriser", "analyser", "comparer", "examiner", "mesurer", "estimer",
    "comprendre", "explorer", "determiner", "evaluer", "expliquer", "interpreter",
    # variantes proches admises (même intention)
    "etudier", "apprecier", "cerner", "approfondir", "questionner", "verifier",
]

# Verbes qui PRÉSUPPOSENT le résultat (neutralité scientifique, SPEC §10.C).
FORBIDDEN_VERBS = [
    "demontrer", "prouver", "demonstration", "confirmer", "etablir", "montrer",
    "justifier", "valider", "attester", "corroborer",
    # formulations assertives typiques
]

# Tournures d'hypothèse : ce n'est pas la place des objectifs (SPEC §7.C).
HYPOTHESIS_MARKERS = [
    r"\bhypoth[eè]se\b", r"\bnous\s+(supposons|pensons|postulons)\b", r"\b(h1|h2|h3)\b",
    r"\bsi\s+.+\s+alors\s+", r"\bon\s+s'attend\s+[àa]\s+ce\s+que\b",
    r"\bil\s+est\s+attendu\s+que\b",
]

# Activités administratives / étapes de rédaction (SPEC §9.3) — sauf consigne explicitement contraire.
ACTIVITY_MARKERS = [
    r"\blire\b[^.]{0,30}\b(articles?|ouvrages?|litt[eé]rature)\b",
    r"\brecens(er|ement)\b[^.]{0,30}\b(litt[eé]rature|articles?|ouvrages?)\b",
    r"\br[eé]diger\b", r"\b[dé]?poser\s+le\s+m[eé]moire\b", r"\bfaire\s+une\s+bibliographie\b",
    r"\bcollecter\s+des\s+donn[eé]es\b$", r"\bcompiler\b",
]

# Marqueurs d'une consigne universitaire explicite demandant des ACTIVITÉS (lève l'interdit).
_ACTIVITY_INSTRUCTION = re.compile(
    r"(activit[eé]s?\s+(du|de)|plan\s+de\s+travail|d[eé]crire\s+les\s+[eé]tapes)", re.IGNORECASE)

_VERB_RE = re.compile(r"^[^a-zà-ÿ]*([a-zà-ÿ]+)")
_DIMENSION_STOPWORDS = {"les", "des", "une", "pour", "dans", "par", "sur", "avec", "afin", "que"}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip()


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", _normalize(text)) if w not in _DIMENSION_STOPWORDS}


def opening_verb(text: str) -> str:
    """Verbe d'ouverture d'un objectif (« Analyser … » -> « analyser »)."""
    match = _VERB_RE.search((text or "").strip().lower())
    return _normalize(match.group(1)).strip() if match else ""


def has_action_verb(text: str) -> bool:
    verb = opening_verb(text)
    if not verb:
        return False
    if verb in ACTION_VERBS:
        return True
    # Tolérance sur les variantes de flexion/terminaison (analyser → analyse, examiner → examen…).
    return any(verb.startswith(v[:5]) and v[:5] for v in ACTION_VERBS if len(v) >= 5)


def forbidden_verb_hits(text: str) -> list[str]:
    norm = _normalize(text)
    hits = []
    for verb in FORBIDDEN_VERBS:
        if re.search(rf"\b{verb}", norm):
            hits.append(verb)
    return hits


def looks_like_hypothesis(text: str) -> list[str]:
    return [pat for pat in HYPOTHESIS_MARKERS if re.search(pat, (text or "").lower())]


def is_activity(text: str, instructions: str = "") -> list[str]:
    """Activité administrative/rédactionnelle — sauf consigne universitaire contraire explicite."""
    if _ACTIVITY_INSTRUCTION.search(instructions or ""):
        return []
    norm = _normalize(text)
    return [pat for pat in ACTIVITY_MARKERS if re.search(pat, norm)]


def redundancy(first: str, second: str, threshold: float = 0.5) -> bool:
    """Vrai si deux objectifs se recouvrent fortement (recouvrement de Jaccard des mots-clés)."""
    a, b = tokens(first), tokens(second)
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= threshold


def redundant_pairs(objectives: list[str], threshold: float = 0.5) -> list[tuple[int, int]]:
    pairs = []
    for i in range(len(objectives)):
        for j in range(i + 1, len(objectives)):
            if redundancy(objectives[i], objectives[j], threshold):
                pairs.append((i + 1, j + 1))
    return pairs


def is_too_short(text: str, min_tokens: int = 4) -> bool:
    return len(tokens(text)) < min_tokens


# --- délimitation : une zone/période/population ajoutée sans source est DÉCLARÉE (SPEC §10.D) -----
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2}|21\d{2})\b")
_PARTS_RE = re.compile(r"\s*[,;/]\s*|\s+et\s+|\s+puis\s+|\s+-\s+")


def _boundary_parts(normalized_value: str) -> list[str]:
    return [part.strip() for part in _PARTS_RE.split(normalized_value) if part.strip()]


def unsourced_boundaries(scope, provided_text: str) -> dict:
    """Délimitations présentes dans les objectifs mais absentes des entrées fournies.

    Aucune invention tolérée : une délimitation composée est acceptée dès lors que CHACUN de ses
    éléments est fourni (pays + zone dans des champs distincts).
    """
    haystack = _normalize(provided_text)
    out: dict[str, str] = {}
    for field_name, value in (("geo", getattr(scope, "geo", "") or ""),
                              ("population", getattr(scope, "population", "") or ""),
                              ("temps", getattr(scope, "temps", "") or "")):
        value = str(value).strip()
        if not value:
            continue
        normalized = _normalize(value)
        if normalized and normalized in haystack:
            continue
        parts = _boundary_parts(normalized)
        if len(parts) > 1 and all(part in haystack for part in parts):
            continue
        if field_name == "temps":
            years = _YEAR_RE.findall(value)
            if years and all(year in haystack for year in years):
                continue
        out[field_name] = value
    return out


def unsourced_years(objectives_text: str, provided_text: str) -> list[str]:
    """Années citées dans les objectifs mais absentes des entrées fournies (période inventée)."""
    haystack = _normalize(provided_text)
    found = _YEAR_RE.findall(objectives_text or "")
    return sorted({year for year in found if year not in haystack})
