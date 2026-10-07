"""Règles de sécurité de l'Agent Problème (SPEC §10, §13).

Spécificité de cet agent : les contenus récupérés sur le web sont une surface d'attaque
supplémentaire (OWASP LLM01/LLM04). Ils sont donc scannés et balisés comme les entrées
étudiantes.
"""

import re

# Motifs d'injection de prompt / tentative de détournement.
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
    # Motifs propres aux contenus récupérés : instructions cachées dans une page/source.
    r"(assistant|mod[èe]le)[^\n]{0,30}(tu dois|vous devez|must)\s+(r[ée]pondre|valider|écrire)",
    r"(valide|accepted?|approuve)[^\n]{0,20}(cette|ce)\s+(fiche|sortie|r[ée]ponse)",
]

# Motifs de secret à ne jamais laisser fuiter.
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{16,}",                      # OpenAI / DeepSeek style
    r"AIza[0-9A-Za-z_\-]{20,}",                   # Google API key
    r"ghp_[A-Za-z0-9]{20,}",                      # GitHub token
    r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}",
    r"(?i)(api[_\-]?key|secret|password|token)\s*[:=]\s*\S+",
]

# Balises d'enveloppe des données non fiables (fuite d'instructions si présentes en sortie).
UNTRUSTED_TAGS = [
    "sujet_non_fiable",
    "contexte_non_fiable",
    "observations_non_fiable",
    "source_web_non_fiable",
    "reponses_precedentes_non_fiable",
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
    """Remplace tout secret reconnaissable par un marqueur, avant log ou stockage."""
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
    return (
        f"<{label}_non_fiable>\n"
        f"{text}\n"
        f"</{label}_non_fiable>"
    )
