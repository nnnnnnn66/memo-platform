"""Règles déterministes de neutralité et de formulation (SPEC §10.C, §10.D, §9.3-9.4).

Cœur anti-présupposé : une question qui suppose déjà sa réponse (« Pourquoi cette politique est-elle
inefficace ? » alors que l'inefficacité n'est pas établie) doit être détectée par le CODE, pas
seulement demandée au modèle. Ces règles sont volontairement conservatrices : en cas de doute, elles
signalent (l'humain tranche) plutôt que d'accepter en silence.
"""

import re
import unicodedata

# Marqueurs d'une prémisse négative/positive assertée dans la question.
_PREMISE_MARKERS = [
    "inefficace", "inefficaces", "inefficacite", "echec", "echecs", "defaillance", "defaillances",
    "insuffisant", "insuffisants", "insuffisance", "inadapte", "inadaptee", "inadaptes",
    "mauvais", "mauvaise", "probleme", "problematique", "crise", "faillite", "carence",
    "corruption", "incompetence", "sous-performance", "contre-performance", "obsolete",
    "réussi", "reussi", "succes", "benefique", "avantageux",
]

# Formes interrogatives « à présupposé » : elles impliquent un constat non démontré.
_PRESUPPOSITION_PATTERNS = [
    r"\bpourquoi\b[^?]{0,90}",
    r"\bqu'?est-?ce qui (explique|provoque|cause)\b",
    r"\bcomment\b[^?]{0,40}\b(r[ée]soudre|rem[ée]dier|corriger|lutter|am[ée]liorer)\b",
    r"\ben quoi\b[^?]{0,60}\b(est|sont|échoue|échouent)\b",
    r"\bdans quelle mesure\b[^?]{0,60}\b(ne\b[^?]{0,30}\bpas|échoue|échouent)\b",
]

# Mots interrogatifs : plus d'un ⇒ question double. Les tournures figées multi-mots sont
# neutralisées avant comptage (sinon « dans quelle mesure » compterait deux fois).
_INTERROGATIVES = [
    r"\bpourquoi\b", r"\bcomment\b", r"\bcombien\b", r"\bquand\b", r"\boù\b", r"\bqui\b",
    r"\bquel(?:le|s|les)?\b", r"\bqu'?est-?ce\b",
]

_FIXED_TURNS = re.compile(r"dans quelle mesure|en quoi|à quel point|qu'?est-?ce qui|qu'?est-?ce que")

_MIN_TOKENS = 6


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{3,}", _normalize(text))


def detect_premises(question: str) -> list[str]:
    """Marqueurs de prémisse (négative ou positive) présents dans la question."""
    norm = _normalize(question)
    return [marker for marker in _PREMISE_MARKERS if re.search(rf"\b{marker}\b", norm)]


def detect_presupposition(question: str) -> list[str]:
    """Formes interrogatives porteuses de présupposé (« pourquoi… », « comment remédier… »)."""
    if not question:
        return []
    return [pat for pat in _PRESUPPOSITION_PATTERNS if re.search(pat, question, re.IGNORECASE)]


def is_double_question(question: str) -> bool:
    """Vrai si la question en contient plusieurs (plus d'un mot interrogatif, ou « ? » multiple)."""
    if not question:
        return False
    if question.count("?") > 1:
        return True
    # Les tournures figées (« dans quelle mesure »…) comptent pour UNE seule question.
    scrubbed = _FIXED_TURNS.sub(" ", question)
    hits = sum(1 for pat in _INTERROGATIVES if re.search(pat, scrubbed, re.IGNORECASE))
    return hits > 1


def is_too_broad(question: str) -> bool:
    """Vrai si la question est trop courte/générale pour guider une investigation."""
    return len(_tokens(question)) < _MIN_TOKENS


def premise_is_grounded(premise: str, context_text: str) -> bool:
    """Le présupposé est-il étayé par la problématique/sujet fournis ? (recouvrement lexical)."""
    if not premise:
        return False
    return premise in _normalize(context_text)


# --- délimitation : une zone/période/population ajoutée sans source est DÉCLARÉE -------------------

_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2}|21\d{2})\b")

# Une délimitation peut être COMPOSÉE (« Côte d'Ivoire, Abidjan », « Abidjan et Bouaké ») alors que
# l'étudiant fournit ses éléments dans des champs DISTINCTS (pays / zone géographique). Exiger la
# chaîne entière comme bloc contigu signalerait à tort une délimitation pourtant fournie — constaté
# au test réel (F5 refusait « geo=Côte d'Ivoire, Abidjan »). On vérifie donc chaque élément.
_PARTS_RE = re.compile(r"\s*[,;/]\s*|\s+et\s+|\s+puis\s+|\s+-\s+")


def _boundary_parts(normalized_value: str) -> list[str]:
    """Éléments d'une délimitation composée (chaque élément doit être sourcé séparément)."""
    return [part.strip() for part in _PARTS_RE.split(normalized_value) if part.strip()]


# Citations d'une information de l'étudiant : guillemets français, anglais ou courbes. On ne
# retient PAS l'apostrophe droite, omniprésente en français (« d'Ivoire », « qu'elle »).
_CITATION_RES = (
    re.compile(r"«([^»]+)»"),
    re.compile(r"“([^”]+)”"),
    re.compile(r'"([^"]+)"'),
)
# Longueur minimale (normalisée) d'une citation pour valoir preuve : « Abidjan » suffit, « a » non.
_MIN_CITED_CHARS = 4


def cited_fragments(value: str) -> list[str]:
    """Fragments cités entre guillemets, dans l'ordre d'apparition."""
    fragments: list[str] = []
    for pattern in _CITATION_RES:
        fragments.extend(pattern.findall(str(value or "")))
    return [fragment.strip() for fragment in fragments if fragment.strip()]


def is_cited_from_student(value: str, haystack: str) -> bool:
    """Vrai si la valeur porte une citation EXACTE d'un mot de l'étudiant (fragment verbatim).

    C'est la règle « attribuée ET citée ⇒ acceptée » : l'agent peut reformuler une délimitation
    dans sa langue, à condition de citer mot pour mot le libellé de l'étudiant entre guillemets.
    Un fragment cité mais INTROUVABLE dans les données fournies ne vaut rien (citation fabriquée).
    """
    for fragment in cited_fragments(value):
        normalized = _normalize(fragment)
        if len(normalized) >= _MIN_CITED_CHARS and normalized in haystack:
            return True
    return False


def unsourced_boundaries(scope, provided_text: str) -> dict:
    """Repère les délimitations présentes dans la question mais absentes des entrées fournies.

    Aucune invention n'est tolérée : si l'agent délimite (zone, période, population) sans que cela
    figure dans les données de l'étudiant, c'est signalé — jamais accepté en silence.
    Une délimitation est SOURCÉE si l'une de ces conditions tient :
      - sa forme normalisée figure verbatim dans les données fournies ;
      - une délimitation composée dont CHACUN des éléments figure dans les données fournies ;
      - une période dont toutes les années figurent déjà dans les données fournies ;
      - elle porte une CITATION EXACTE (entre guillemets) d'un libellé de l'étudiant présent dans
        les données fournies — l'agent attribue alors explicitement à l'étudiant le mot qu'il cite.
    Hors de ces cas, la délimitation est signalée : la règle reste STRICTE, une délimitation sans
    source (même correctement attribuée mais non citée) n'est jamais acceptée en silence.
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
        # Une période sous forme d'années est acceptée si les années figurent déjà dans les entrées.
        if field_name == "temps":
            years = _YEAR_RE.findall(value)
            if years and all(year in haystack for year in years):
                continue
        # Attribuée ET citée : l'agent cite mot pour mot un libellé de l'étudiant.
        if is_cited_from_student(value, haystack):
            continue
        out[field_name] = value
    return out
