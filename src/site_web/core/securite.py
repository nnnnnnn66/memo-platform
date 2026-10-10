"""Sécurité du site — bibliothèque standard uniquement (aucune dépendance, aucun service).

Mots de passe : `scrypt` (fonction de dérivation lente, paramétrée), sel unique par compte.
Sessions : jetons aléatoires conservés CÔTÉ SERVEUR — le navigateur ne reçoit qu'un identifiant
opaque, jamais une donnée signée qu'il pourrait modifier.
Formulaires : jeton anti-CSRF à chaque envoi.
"""

import hashlib
import hmac
import secrets

# Paramètres scrypt : coût mémoire ~16 Mo, coût CPU modéré — suffisant et supportable sur le VPS.
_N, _R, _P, _DK = 2 ** 14, 8, 1, 32


def hacher(mot_de_passe: str) -> str:
    """Empreinte stockable d'un mot de passe (jamais le mot de passe lui-même)."""
    sel = secrets.token_bytes(16)
    empreinte = hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=sel,
                               n=_N, r=_R, p=_P, dklen=_DK)
    return f"scrypt${sel.hex()}${empreinte.hex()}"


def verifier(mot_de_passe: str, enregistre: str) -> bool:
    """Vérification à TEMPS CONSTANT (aucune fuite par la durée de comparaison)."""
    try:
        algorithme, sel_hex, attendu_hex = (enregistre or "").split("$")
        if algorithme != "scrypt":
            return False
        calcule = hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=bytes.fromhex(sel_hex),
                                 n=_N, r=_R, p=_P, dklen=_DK)
        return hmac.compare_digest(calcule.hex(), attendu_hex)
    except (ValueError, AttributeError):
        return False


def jeton() -> str:
    """Jeton aléatoire (session, invitation, CSRF) — 256 bits d'entropie."""
    return secrets.token_urlsafe(32)


def mot_de_passe_valide(mot_de_passe: str) -> tuple:
    """Règle simple et expliquée : longueur d'abord, pas de zoo de caractères obligatoires."""
    if len(mot_de_passe or "") < 10:
        return False, "Votre mot de passe doit contenir au moins 10 caractères."
    if mot_de_passe.strip() != mot_de_passe:
        return False, "Votre mot de passe ne doit pas commencer ou finir par un espace."
    return True, ""


# Alphabet SANS caractères ambigus (ni 0/O, ni 1/l/I) : le mot de passe est recopié à la main
# depuis un courrier, une confusion coûterait une connexion impossible.
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def mot_de_passe_aleatoire(groupes: int = 3, taille: int = 4) -> str:
    """Mot de passe fort ET lisible par groupes : « kfqm-2xta-9prz » (~60 bits d'entropie)."""
    return "-".join(
        "".join(secrets.choice(_ALPHABET) for _ in range(taille)) for _ in range(groupes))
