"""Règles de sécurité de l'Agent Diagnostic méthodologique.

Surfaces propres à cet agent : tout le dossier de recherche (sujet, problème, problématique, question,
objectifs, hypothèses, littérature), les données/terrain/ressources disponibles, la méthodologie
existante, les contraintes et consignes. Tout est DONNÉE NON FIABLE. Aucun contrat d'ancrage
bibliographique ici : la sécurité porte sur l'injection et les secrets, plus les contrôles
déterministes de `analysis/`.
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
    # Consignes piégées visant la validation ou l'orientation de la question.
    r"(assistant|mod[èe]le|agent)[^\n]{0,30}(tu dois|vous devez|must)\s+(r[ée]pondre|valider|écrire|r[ée]diger)",
    r"(valide|accepted?|approuve)[^\n]{0,20}(cette|ce)\s+(fiche|sortie|r[ée]ponse|question|probl[ée]matique)",
    r"(invente|fabrique|cr[ée]e)[^\n]{0,30}(donn[ée]e|population|terrain|p[ée]riode|r[ée]sultat)",
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
    "problematique_non_fiable",
    "question_recherche_non_fiable",
    "questions_secondaires_non_fiable",
    "objectif_general_non_fiable",
    "objectifs_specifiques_non_fiables",
    "hypotheses_non_fiables",
    "litterature_non_fiable",
    "donnees_disponibles_non_fiables",
    "acces_terrain_non_fiable",
    "ressources_disponibles_non_fiables",
    "methodologie_existante_non_fiable",
    "contexte_non_fiable",
    "contraintes_non_fiables",
    "consignes_universitaires_non_fiables",
    "consignes_directeur_non_fiables",
    "reponses_precedentes_non_fiables",
    "donnees_etudiant_non_fiables",
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


def looks_truncated(text: str) -> bool:
    """Heuristique : un JSON qui ne se termine pas par « } » est probablement tronqué."""
    return bool(text) and not text.rstrip().endswith("}")
