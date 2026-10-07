"""Règles de sécurité de l'Agent Problématique.

Surfaces propres à cet agent : sujet, problème, observations de terrain et consignes du directeur
fournies par l'étudiant, plus les CONTENUS DOCUMENTAIRES issus de la revue de littérature (titres,
résumés, citations, texte intégral). Tout est DONNÉE NON FIABLE.

L'ancrage verbatim vit ici : c'est le cœur anti-hallucination de l'étape 4.
"""

import re

INJECTION_PATTERNS = [
    r"ignore[^\n]{0,40}(instructions|consignes|règles)",
    r"(oublie|ignore)[^\n]{0,40}(tout|tes|vos)",
    r"(system\s*prompt|prompt\s*syst[èe]me)",
    r"(donne|r[ée]v[èe]le|affiche|montre)[^\n]{0,40}(instructions?|prompt|r[èe]gles?|cl[ée]|token|secret)",
    r"(ta|votre|la)\s+cl[ée]\s*(api|d'api)",
    r"(execute|ex[ée]cute|lance)[^\n]{0,30}(commande|shell|bash|script)",
    r"(print|show|reveal)\s+(your\s+)?(system\s+)?(prompt|instructions)",
    r"tu es maintenant|you are now|from now on",
    r"jailbreak|DAN mode",
    # Contenus documentaires : instructions cachées visant l'agent ou la validation.
    r"(assistant|mod[èe]le|agent)[^\n]{0,30}(tu dois|vous devez|must)\s+(r[ée]pondre|valider|écrire|citer)",
    r"(valide|accepted?|approuve)[^\n]{0,20}(cette|ce)\s+(fiche|sortie|r[ée]ponse|note|probl[ée]matique)",
    r"(cite|reference)\s+(cette|ce)\s+(source|document|auteur)\s+(sans|m[êe]me si)",
    r"(invente|fabrique|cr[ée]e)[^\n]{0,30}(citation|r[ée]f[ée]rence|statistique|lacune)",
]

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{16,}",
    r"AIza[0-9A-Za-z_\-]{20,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}",
    r"(?i)(api[_\-]?key|secret|password|token)\s*[:=]\s*\S+",
]

UNTRUSTED_TAGS = [
    "sujet_non_fiable",
    "probleme_non_fiable",
    "contexte_non_fiable",
    "observations_terrain_non_fiables",
    "consignes_directeur_non_fiables",
    "donnees_etudiant_non_fiables",
    "corpus_amont_non_fiable",
    "document_amont_non_fiable",
    "passage_amont_non_fiable",
    "revue_litterature_non_fiable",
]


def scan_injection(text: str) -> list[str]:
    """Retourne les motifs d'injection détectés dans un texte non fiable."""
    if not text:
        return []
    hits = []
    for pat in INJECTION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            hits.append(pat)
    return hits


def redact(text: str) -> str:
    if not text:
        return text
    out = text
    for pat in SECRET_PATTERNS:
        out = re.sub(pat, "[REDACTED]", out)
    return out


def contains_secret(text: str) -> bool:
    if not text:
        return False
    return any(re.search(pat, text) for pat in SECRET_PATTERNS)


def wrap_untrusted(label: str, text: str) -> str:
    """Balisage explicite des données non fiables : jamais des instructions."""
    text = text or ""
    return f"<{label}_non_fiable>\n{text}\n</{label}_non_fiable>"


# --- normalisation utilisée pour l'ancrage verbatim des citations -------------------------------

_WS = re.compile(r"\s+")


def normalize_for_quote(text: str) -> str:
    """Normalisation tolérante pour vérifier qu'une citation existe dans le texte réel.

    Retire les accents, la casse, la ponctuation de césure et compresse les espaces : une citation
    valide reste trouvable malgré les différences de mise en page du PDF.
    """
    import unicodedata

    if not text:
        return ""
    t = text.replace("\u00ad", "").replace("\u2010", "-").replace("\u2011", "-")
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = t.replace("-\n", "").replace("\n", " ")
    return _WS.sub(" ", t).lower().strip()


def quote_is_anchored(quote: str, text: str, min_chars: int = 25) -> bool:
    """Vrai si `quote` existe littéralement (normalisé) dans `text`.

    Leçon de l'étape 3 : une boucle de segmentation vide faisait « fail-open » et acceptait toute
    citation inventée de 25 à 60 caractères. Ici, une citation trop courte pour être découpée et non
    trouvée littéralement est REJETÉE — jamais d'acceptation par défaut.
    """
    q = normalize_for_quote(quote)
    if len(q) < min_chars:
        return False
    n = normalize_for_quote(text)
    if not n:
        return False
    if q in n:
        return True
    # Citation longue : acceptée si TOUS ses segments sont présents (absorbe les coupures de
    # page/colonne sans laisser passer une citation inventée).
    if len(q) <= 60:
        return False
    segments = [q[index:index + 120] for index in range(0, len(q) - 60, 200)]
    if not segments:
        return False
    return all(segment in n for segment in segments)


def looks_truncated(text: str) -> bool:
    """Heuristique : un JSON qui ne se termine pas par « } » est probablement tronqué."""
    return bool(text) and not text.rstrip().endswith("}")
