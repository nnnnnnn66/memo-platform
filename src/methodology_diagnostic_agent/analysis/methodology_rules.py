"""Règles déterministes du diagnostic méthodologique (SPEC §7, §10).

Cœur de la distinction des catégories : approche, logique de raisonnement, type de recherche,
stratégie, technique de collecte et méthode d'analyse ne sont PAS interchangeables. Garde-fous de
neutralité : aucune causalité sans dispositif adéquat, analyse compatible avec l'approche. Ces
contrôles sont CODÉS : en cas de doute, ils signalent — l'humain tranche.
"""

import re
import unicodedata

# --- énumérations canoniques des six catégories (SPEC §7) -----------------------------------------
APPROACHES = ["qualitative", "quantitative", "mixte", "autre"]
LOGICS = ["inductive", "deductive", "hypothetico_deductive", "abductive", "autre"]
RESEARCH_TYPES = ["exploratoire", "descriptive", "explicative", "comparative", "evaluative",
                  "experimentale", "autre"]
STRATEGIES = ["enquete", "etude_de_cas", "experimentation", "analyse_documentaire",
              "etude_comparative", "recherche_action", "donnees_secondaires", "autre"]

_ALIASES = {
    # approche
    "qualitatif": "qualitative", "qualitative": "qualitative", "qualitatives": "qualitative",
    "quantitatif": "quantitative", "quantitative": "quantitative", "quantitatives": "quantitative",
    "mixte": "mixte", "mixed": "mixte", "mixte (qualitative et quantitative)": "mixte",
    # logique
    "inductif": "inductive", "inductive": "inductive", "induction": "inductive",
    "deductif": "deductive", "deductive": "deductive", "deduction": "deductive",
    "hypothetico_deductif": "hypothetico_deductive", "hypothetico-deductif": "hypothetico_deductive",
    "hypothetico deductive": "hypothetico_deductive", "hypothetico_deductive": "hypothetico_deductive",
    "abductif": "abductive", "abductive": "abductive", "abduction": "abductive",
    # type
    "exploratoire": "exploratoire", "descriptif": "descriptive", "descriptive": "descriptive",
    "explicatif": "explicative", "explicative": "explicative", "comparatif": "comparative",
    "comparative": "comparative", "evaluatif": "evaluative", "evaluative": "evaluative",
    "experimental": "experimentale", "experimentale": "experimentale",
    # stratégie
    "enquete": "enquete", "survey": "enquete", "sondage": "enquete",
    "etude de cas": "etude_de_cas", "etude_de_cas": "etude_de_cas", "cas": "etude_de_cas",
    "experimentation": "experimentation", "experience": "experimentation",
    "analyse documentaire": "analyse_documentaire", "analyse_documentaire": "analyse_documentaire",
    "documentaire": "analyse_documentaire",
    "etude comparative": "etude_comparative", "etude_comparative": "etude_comparative",
    "recherche action": "recherche_action", "recherche_action": "recherche_action",
    "donnees secondaires": "donnees_secondaires", "donnees_secondaires": "donnees_secondaires",
}

_CATEGORIES = {
    "approche": APPROACHES,
    "logique": LOGICS,
    "type_recherche": RESEARCH_TYPES,
    "strategie": STRATEGIES,
}

# Mots-clés d'une méthode d'analyse statistique inférentielle (incompatible avec du qualitatif pur).
_INFERENTIAL = ["inferentielle", "test statistique", "regression", "correlation", "anova",
                "khi deux", "khi-deux", "chi deux", "significativite"]
# Mots-clés d'une analyse proprement qualitative.
_QUALITATIVE_ANALYSIS = ["thematique", "analyse de contenu", "analyse narrative", "codage",
                         "analyse du discours", "analyse interpretative"]

# Verbe/mot-clé de causalité (SPEC §10.8-10.9 : ne pas démontrer une causalité sans dispositif).
_CAUSAL_MARKERS = ["cause", "provoque", "entraine", "est a l'origine", "effet causal",
                   "demontre une causalite", "demontrer une causalite", "causalite"]

_VERB_RE = re.compile(r"^[^a-zà-ÿ]*([a-zà-ÿ]+)")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^a-z0-9_ -]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", _normalize(text)))


def normalize_code(value: str, category: str) -> str:
    """Ramène une valeur libre à une clé canonique de la catégorie, sinon « autre »."""
    key = _normalize(value).replace(" ", "_")
    allowed = _CATEGORIES.get(category, [])
    if key in allowed:
        return key
    if key in _ALIASES and _ALIASES[key] in allowed:
        return _ALIASES[key]
    spaced = _ALIASES.get(_normalize(value))
    if spaced in allowed:
        return spaced
    for token in _normalize(value).split("_"):
        if token in allowed:
            return token
        if _ALIASES.get(token) in allowed:
            return _ALIASES[token]
    return "autre"


def is_known(value: str, category: str) -> bool:
    return normalize_code(value, category) in _CATEGORIES.get(category, [])


def causal_hits(text: str) -> list[str]:
    norm = _normalize(text)
    return [m for m in _CAUSAL_MARKERS if m in norm]


def causality_is_justified(strategy_code: str) -> bool:
    """Seul un dispositif expérimental (ou quasi) autorise une lecture causale (SPEC §10.8)."""
    return strategy_code in ("experimentation",)


def analysis_incompatible(approach_code: str, analyse_texts: list[str]) -> list[str]:
    """Signale une incohérence entre l'approche et les méthodes d'analyse proposées."""
    blob = _normalize(" ; ".join(analyse_texts))
    issues: list[str] = []
    if approach_code == "qualitative" and any(m in blob for m in _INFERENTIAL):
        issues.append(
            "approche qualitative mais méthodes d'analyse statistique inférentielle proposées")
    if approach_code == "quantitative" and any(m in blob for m in _QUALITATIVE_ANALYSIS) \
            and not any(m in blob for m in _INFERENTIAL):
        issues.append(
            "approche quantitative mais uniquement des analyses qualitatives proposées")
    return issues


def same_text(first: str, second: str, threshold: float = 0.75) -> bool:
    """Deux formulations quasi identiques (recouvrement de mots-clés) — anti-fusion de catégories."""
    a, b = tokens(first), tokens(second)
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= threshold
