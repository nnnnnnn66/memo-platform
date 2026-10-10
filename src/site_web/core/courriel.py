"""Courriers électroniques du site — bibliothèque standard (`smtplib`), aucun service payant.

**État : module PRÊT mais non branché.** L'inscription ne l'utilise pas : à l'inscription,
l'étudiant choisit lui-même son mot de passe et le confirme (décision du porteur de projet).

Il existe pour la seule chose que le site ne sait pas encore faire : **« mot de passe oublié »**.
Aujourd'hui, un étudiant qui perd son mot de passe n'a plus aucun moyen d'entrer — c'est le
prochain trou à combler, et tout est déjà là : il suffira d'un écran, d'une route, et du compte
d'envoi posé par `/root/poser-compte-envoi.sh` (variables MEMO_SMTP_* dans ~/.hermes/.env).

Ce module ne lève jamais d'exception non maîtrisée vers une page : une panne d'envoi devient un
message clair pour l'étudiant.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage

NOM_EXPEDITEUR = "Accompagnement du mémoire"
DELAI = 25


class ErreurCourriel(Exception):
    """Échec d'envoi — le message est destiné à l'écran, jamais une trace technique."""


def configuration() -> dict | None:
    """Réglages SMTP lus dans l'environnement (donc dans ~/.hermes/.env). None si non configuré."""
    hote = (os.environ.get("MEMO_SMTP_HOST") or "").strip()
    if not hote:
        return None
    utilisateur = (os.environ.get("MEMO_SMTP_USER") or "").strip()
    return {
        "hote": hote,
        "port": int((os.environ.get("MEMO_SMTP_PORT") or "587").strip()),
        "utilisateur": utilisateur,
        "mot_de_passe": os.environ.get("MEMO_SMTP_PASSWORD") or "",
        "expediteur": (os.environ.get("MEMO_SMTP_FROM") or "").strip() or utilisateur,
    }


def est_configure() -> bool:
    return configuration() is not None


def envoyer(destinataire: str, sujet: str, texte: str, transport=None) -> None:
    """Envoie un courrier en texte brut. `transport` permet de simuler l'envoi dans les tests."""
    reglages = configuration()
    if reglages is None:
        raise ErreurCourriel("L'envoi de courrier n'est pas configuré sur cette plateforme.")

    message = EmailMessage()
    message["Subject"] = sujet
    message["From"] = f"{NOM_EXPEDITEUR} <{reglages['expediteur']}>"
    message["To"] = destinataire
    message.set_content(texte)

    if transport is not None:
        transport(message)
        return

    contexte = ssl.create_default_context()
    try:
        with smtplib.SMTP(reglages["hote"], reglages["port"], timeout=DELAI) as serveur:
            serveur.starttls(context=contexte)
            if reglages["utilisateur"]:
                serveur.login(reglages["utilisateur"], reglages["mot_de_passe"])
            serveur.send_message(message)
    except Exception as erreur:  # noqa: BLE001 — toute panne devient un message pour l'étudiant
        raise ErreurCourriel(
            "Le courrier n'a pas pu être envoyé. Vérifiez l'adresse saisie, puis réessayez dans "
            "quelques instants.") from erreur


# --------------------------------------------------------------------- messages
def courrier_acces(email: str, mot_de_passe: str, adresse_site: str) -> tuple:
    """Le courrier qui remet son mot de passe à un nouvel étudiant."""
    sujet = "Votre mot de passe — accompagnement du mémoire"
    texte = f"""Bonjour,

Un accès vient d'être créé sur la plateforme d'accompagnement méthodologique du mémoire avec
cette adresse : {email}

Votre mot de passe :

    {mot_de_passe}

Pour entrer : {adresse_site}/connexion

Ce mot de passe est personnel : il protège votre mémoire et personne d'autre n'y a accès. Si vous
n'êtes pas à l'origine de cette demande, ignorez simplement ce message — aucun accès ne sera
utilisé sans ce mot de passe.

Bonne rédaction,
{NOM_EXPEDITEUR}
"""
    return sujet, texte


def courrier_rappel(email: str, mot_de_passe: str, adresse_site: str) -> tuple:
    """Renvoyer le mot de passe à quelqu'un qui l'a perdu (même contenu, autre ton)."""
    sujet = "Votre mot de passe — accompagnement du mémoire"
    texte = f"""Bonjour,

Vous avez demandé à recevoir votre mot de passe pour la plateforme d'accompagnement du mémoire
(adresse : {email}).

Votre mot de passe :

    {mot_de_passe}

Pour entrer : {adresse_site}/connexion

Si vous n'avez rien demandé, changez ce mot de passe dès votre prochaine connexion.

{NOM_EXPEDITEUR}
"""
    return sujet, texte
