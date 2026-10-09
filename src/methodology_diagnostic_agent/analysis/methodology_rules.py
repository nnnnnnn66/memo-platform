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

# Techniques de COLLECTE qualitatives vs quantitatives (cohérence approche ↔ collecte).
# Le vérificateur a relevé en campagne réelle : « un volet entretiens est listé alors que l'approche
# est déclarée quantitative mono-méthode » — questionnaire (quantitatif) + entretiens (qualitatif)
# sous une approche mono-méthode : c'est une approche MIXTE qu'il faut déclarer (SPEC §7.A).
_QUALITATIVE_COLLECT = ["entretien", "entretiens", "focus group", "groupe de discussion",
                        "observation", "observations", "recit de vie", "recits de vie",
                        "analyse documentaire qualitative", "histoire de vie"]
_QUANTITATIVE_COLLECT = ["questionnaire", "questionnaires", "sondage", "sondages", "echelle",
                         "echelles", "releve", "releves", "base de donnees", "bases de donnees",
                         "donnees secondaires", "donnees statistiques"]

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


# Mots qui DEMENTENT une lecture causale. Le mot « causalite » dans une phrase qui l'ECARTE
# (« sans pretendre a une causalite », « ne permet pas d'etablir une causalite ») n'est pas une
# affirmation de causalite : le signaler serait un faux positif. Constat en campagne reelle
# (agent 8) : le modele ecrivait « sans pretendre a une causalite (aucun dispositif experimental) »
# — donc correctement — et la campagne levait sur M4 apres ses deux tentatives, le modele ne
# pouvant pas « corriger » une phrase juste.
_CAUSAL_NEGATIONS = frozenset({
    "sans", "pas", "aucun", "aucune", "aucuns", "aucunes", "jamais", "non", "ni",
    "exclut", "exclure", "ecarte", "ecarter", "refuse", "refuser", "impossible",
    "interdit", "interdire", "hors",
})
# Fenetre mesuree en MOTS (et non en caracteres) : « sans » ou « pas » doit etre dans la meme
# proposition que le marqueur. Trop large, « Sans surprise, le dispositif demontre une causalite »
# serait absous a tort.
_NEGATION_WORDS_BEFORE = 4
_NEGATION_WORDS_AFTER = 3


def _marker_is_denied(norm: str, index: int, length: int) -> bool:
    """Vrai si le marqueur est accompagne d'un mot qui le dementit."""
    avant = re.findall(r"[a-z]+", norm[:index])[-_NEGATION_WORDS_BEFORE:]
    apres = re.findall(r"[a-z]+", norm[index + length:])[:_NEGATION_WORDS_AFTER]
    return bool((set(avant) | set(apres)) & _CAUSAL_NEGATIONS)


def causal_hits(text: str) -> list[str]:
    """Marqueurs causaux REELLEMENT affirmes (une denegation ne compte pas)."""
    norm = _normalize(text)
    hits: list[str] = []
    for marker in _CAUSAL_MARKERS:
        start = 0
        while True:
            index = norm.find(marker, start)
            if index < 0:
                break
            if not _marker_is_denied(norm, index, len(marker)):
                hits.append(marker)
                break
            start = index + len(marker)
    return hits


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


def collecte_incompatible(approach_code: str, collecte_texts: list[str]) -> list[str]:
    """Cohérence approche ↔ techniques de COLLECTE (SPEC §7.A, §10.4-10.5).

    Une approche mono-méthode ne peut pas reposer sur des techniques des deux familles : la présence
    conjointe de collecte qualitative (entretiens, observation…) et quantitative (questionnaire,
    relevés…) exige de déclarer l'approche « mixte ». Relevé par le vérificateur en campagne réelle.
    """
    blob = _normalize(" ; ".join(collecte_texts))
    qual = any(m in blob for m in _QUALITATIVE_COLLECT)
    quan = any(m in blob for m in _QUANTITATIVE_COLLECT)
    issues: list[str] = []
    if approach_code == "quantitative":
        if qual and not quan:
            issues.append("approche quantitative mais uniquement des techniques de collecte "
                          "qualitatives proposées")
        elif qual and quan:
            issues.append("collecte à la fois qualitative et quantitative sous une approche "
                          "quantitative mono-méthode : déclarer l'approche « mixte »")
    elif approach_code == "qualitative":
        if quan and not qual:
            issues.append("approche qualitative mais uniquement des techniques de collecte "
                          "quantitatives proposées")
        elif qual and quan:
            issues.append("collecte à la fois qualitative et quantitative sous une approche "
                          "qualitative mono-méthode : déclarer l'approche « mixte »")
    return issues


def same_text(first: str, second: str, threshold: float = 0.75) -> bool:
    """Deux formulations quasi identiques (recouvrement de mots-clés) — anti-fusion de catégories."""
    a, b = tokens(first), tokens(second)
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= threshold
