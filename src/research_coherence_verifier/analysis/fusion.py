"""Détection des éléments FUSIONNÉS À TORT (SPEC §3 point 8).

Sujet, problème et problématique ne sont pas interchangeables : trois textes distincts expriment trois
niveaux différents. Quand deux d'entre eux sont le MÊME texte (recopié, ou reformulé à la marge), le
dossier a « fusionné à tort » — et aucune étape prise seule ne peut le voir.

Méthode : normalisation (minuscules, accents conservés, ponctuation retirée), découpage en mots
significatifs (≥ 4 caractères, hors mots vides), puis recouvrement de tokens. Aucun modèle, aucun
réseau — uniquement la bibliothèque standard.
"""

import re
import unicodedata

_MOTS_VIDES = {
    "dans", "pour", "avec", "sans", "cette", "cettes", "cette", "cet", "les", "des", "une", "aux",
    "par", "sur", "que", "qui", "quoi", "dont", "quel", "quelle", "quels", "quelles", "est", "sont",
    "ont", "été", "etre", "être", "fait", "faire", "ainsi", "donc", "alors", "plus", "moins", "tout",
    "tous", "toute", "toutes", "notre", "votre", "leur", "leurs", "nous", "vous", "ils", "elles",
    "chez", "entre", "vers", "afin", "comme", "mais", "lors", "apres", "après", "avant", "cela",
    "celui", "celle", "lorsqu", "lorsque", "selon", "travail", "recherche", "etude", "étude",
    "memoir", "memoire", "mémoire", "present", "présent", "projet",
}

#: Seuil de recouvrement au-delà duquel deux textes sont considérés comme LE MÊME texte.
SEUIL_FUSION = 0.70


def normaliser(texte: str) -> str:
    if not texte:
        return ""
    texte = unicodedata.normalize("NFKC", str(texte)).lower()
    texte = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñœæ\s]", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


def tokens(texte: str) -> set[str]:
    return {mot for mot in normaliser(texte).split()
            if len(mot) >= 4 and mot not in _MOTS_VIDES}


def recouvrement(a: str, b: str) -> float:
    """Part des mots significatifs PARTAGÉS, rapportée au plus LONG des deux textes.

    Rapporter au plus court (min) fait déclencher le contrôle dès que deux textes parlent du même
    sujet — ce n'est pas une fusion, c'est un thème commun. Rapporté au plus long, le seuil ne se
    franchit que si l'un reprend réellement l'autre. La recopie directe est en outre détectée par le
    test d'inclusion de `sont_fusionnes`.
    """
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def sont_fusionnes(a: str, b: str, seuil: float = SEUIL_FUSION) -> bool:
    """Vrai si deux textes sont substantiellement le MÊME texte (recopiés ou reformulés à la marge)."""
    na, nb = normaliser(a), normaliser(b)
    if not na or not nb:
        return False
    if len(na) > 40 and (na in nb or nb in na):
        return True          # inclusion textuelle : recopie directe
    return recouvrement(a, b) >= seuil


def indice(a: str, b: str) -> str:
    """Preuve lisible : recouvrement et premier fragment commun."""
    milite = recouvrement(a, b)
    communs = sorted(tokens(a) & tokens(b))[:8]
    return (f"recouvrement des mots significatifs {milite:.0%}"
            + (f" ; termes communs : {', '.join(communs)}" if communs else ""))
