"""Garde numérique (contrôle Q2) : aucun chiffre du texte ne doit sortir du moteur.

C'est la garantie anti-invention STRUCTURELLE de l'étape 10 : un modèle de langue produit volontiers
des moyennes et des pourcentages plausibles ; ici, tout nombre publié doit appartenir à l'ensemble des
valeurs réellement calculées (ou réellement fournies par l'étudiant).
"""

import re

#: Un nombre, éventuellement suivi d'une unité ou d'un pourcentage.
_NUMBER = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(%|pour\s?cent)?")


def numbers_in(text: str) -> list[tuple[str, str]]:
    """Extrait (valeur, unité) de chaque nombre d'un texte."""
    found: list[tuple[str, str]] = []
    for match in _NUMBER.finditer(str(text or "")):
        value = match.group(1).strip()
        unite = "%" if match.group(2) else ""
        found.append((value, unite))
    return found


def is_allowed(value: str, unite: str, allowed: set[str]) -> bool:
    variants = {value, value.replace(".", ","), value.replace(",", ".")}
    if variants & allowed:
        return True
    if unite == "%":
        # Un pourcentage calculé est publié sous la forme « 62 % » : on tolère aussi « 62 ».
        return bool({v.rstrip("0").rstrip(".").rstrip(",") for v in variants} & allowed)
    return False


def check_texts(texts: dict, allowed: set[str]) -> list[str]:
    """Retourne les nombres du texte qui ne figurent pas dans la liste blanche (violations Q2)."""
    violations: list[str] = []
    seen: set[str] = set()
    for label, text in (texts or {}).items():
        for value, unite in numbers_in(text):
            if is_allowed(value, unite, allowed):
                continue
            key = f"{value}{unite}"
            if key in seen:
                continue
            seen.add(key)
            violations.append(
                f"Q2 : la valeur « {value}{unite} » ({label}) ne figure dans aucun calcul réalisé "
                "ni dans les données fournies. Seules les valeurs calculées peuvent être publiées.")
    return violations
