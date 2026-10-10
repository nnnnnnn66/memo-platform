"""État des dossiers : où en est chaque étudiant, et ce que chaque étape a réellement produit.

SQLite de la bibliothèque standard (aucun service à installer, aucun coût). Trois tables :
- `dossiers` : un dossier par (étudiant, session) ;
- `etapes`   : le statut de chaque étape, son verdict, la décision de l'étudiant, son résultat ;
- `quota`    : le compteur d'analyses par étudiant et par jour.

Règle tenue ici : le résultat d'une étape n'est **remplacé** que par le résultat d'une nouvelle
exécution de CETTE étape. Aucune écriture croisée entre dossiers.
"""

import datetime
import json
import pathlib
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS dossiers (
    etudiant   TEXT NOT NULL,
    session    TEXT NOT NULL,
    sujet      TEXT NOT NULL DEFAULT '',
    contexte   TEXT NOT NULL DEFAULT '',
    cree_le    TEXT NOT NULL,
    maj_le     TEXT NOT NULL,
    PRIMARY KEY (etudiant, session)
);
CREATE TABLE IF NOT EXISTS etapes (
    etudiant    TEXT NOT NULL,
    session     TEXT NOT NULL,
    numero      INTEGER NOT NULL,
    statut      TEXT NOT NULL,
    verdict     TEXT NOT NULL DEFAULT '',
    decision    TEXT NOT NULL DEFAULT '',
    commentaire TEXT NOT NULL DEFAULT '',
    resultat    TEXT NOT NULL DEFAULT '',
    maj_le      TEXT NOT NULL,
    PRIMARY KEY (etudiant, session, numero)
);
CREATE TABLE IF NOT EXISTS quota (
    etudiant  TEXT NOT NULL,
    jour      TEXT NOT NULL,
    analyses  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (etudiant, jour)
);
"""

STATUT_A_FAIRE = "a_faire"
STATUT_PROPOSEE = "proposee"
STATUT_VALIDEE = "validee"
STATUT_A_REVISER = "a_reviser"
STATUT_ECHEC = "echec"


def _maintenant() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@contextmanager
def _base(chemin: pathlib.Path):
    chemin = pathlib.Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    try:
        # Le schéma est garanti à CHAQUE ouverture : une lecture sur une base encore vierge
        # (dossier inconnu, premier lancement) doit répondre « rien trouvé », jamais planter.
        connexion.executescript(SCHEMA)
        yield connexion
        connexion.commit()
    finally:
        connexion.close()


def initialiser(chemin: pathlib.Path) -> None:
    with _base(chemin) as base:
        base.executescript(SCHEMA)


def creer_dossier(chemin: pathlib.Path, etudiant: str, session: str,
                  sujet: str = "", contexte: str = "") -> None:
    """Crée le dossier s'il n'existe pas. Ne l'écrase JAMAIS s'il existe déjà."""
    with _base(chemin) as base:
        base.execute(
            "INSERT OR IGNORE INTO dossiers (etudiant, session, sujet, contexte, cree_le, maj_le)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (etudiant, session, sujet, contexte, _maintenant(), _maintenant()))


def dossier(chemin: pathlib.Path, etudiant: str, session: str) -> dict | None:
    with _base(chemin) as base:
        ligne = base.execute("SELECT * FROM dossiers WHERE etudiant = ? AND session = ?",
                             (etudiant, session)).fetchone()
    return dict(ligne) if ligne else None


def statut(chemin: pathlib.Path, etudiant: str, session: str, numero: int) -> dict | None:
    with _base(chemin) as base:
        ligne = base.execute(
            "SELECT * FROM etapes WHERE etudiant = ? AND session = ? AND numero = ?",
            (etudiant, session, numero)).fetchone()
    return dict(ligne) if ligne else None


def etape_courante(chemin: pathlib.Path, etudiant: str, session: str,
                   ordre: list[int]) -> int:
    """Première étape **non validée** du parcours (c'est elle qui est ouverte).

    Si toutes les étapes sont validées, renvoie la dernière : l'appelant décide de la suite
    (vérification globale finale).
    """
    for numero in ordre:
        ligne = statut(chemin, etudiant, session, numero)
        if not ligne or ligne["statut"] != STATUT_VALIDEE:
            return numero
    return ordre[-1]


def enregistrer_resultat(chemin: pathlib.Path, etudiant: str, session: str, numero: int,
                         resultat: dict, verdict: str) -> None:
    """Consigne la proposition d'une étape (et le verdict de SON vérificateur, jamais réécrit)."""
    with _base(chemin) as base:
        base.execute(
            "INSERT INTO etapes (etudiant, session, numero, statut, verdict, resultat, maj_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(etudiant, session, numero) DO UPDATE SET"
            "   statut=excluded.statut, verdict=excluded.verdict,"
            "   resultat=excluded.resultat, decision='', commentaire='', maj_le=excluded.maj_le",
            (etudiant, session, numero, STATUT_PROPOSEE, verdict,
             json.dumps(resultat, ensure_ascii=False), _maintenant()))
        base.execute("UPDATE dossiers SET maj_le = ? WHERE etudiant = ? AND session = ?",
                     (_maintenant(), etudiant, session))


def enregistrer_decision(chemin: pathlib.Path, etudiant: str, session: str, numero: int,
                         decision: str, commentaire: str = "") -> str:
    """Enregistre la décision humaine et renvoie le nouveau statut de l'étape."""
    nouveau = {"accepted": STATUT_VALIDEE, "modified": STATUT_A_REVISER,
               "refused": STATUT_A_REVISER}.get(decision, STATUT_A_REVISER)
    with _base(chemin) as base:
        base.execute(
            "UPDATE etapes SET statut = ?, decision = ?, commentaire = ?, maj_le = ?"
            " WHERE etudiant = ? AND session = ? AND numero = ?",
            (nouveau, decision, commentaire, _maintenant(), etudiant, session, numero))
        base.execute("UPDATE dossiers SET maj_le = ? WHERE etudiant = ? AND session = ?",
                     (_maintenant(), etudiant, session))
    return nouveau


def enregistrer_echec(chemin: pathlib.Path, etudiant: str, session: str, numero: int,
                      motif: str) -> None:
    """Une étape qui échoue est DÉCLARÉE : elle n'est ni validée ni silencieusement ignorée."""
    with _base(chemin) as base:
        base.execute(
            "INSERT INTO etapes (etudiant, session, numero, statut, verdict, commentaire, maj_le)"
            " VALUES (?, ?, ?, ?, 'echec', ?, ?)"
            " ON CONFLICT(etudiant, session, numero) DO UPDATE SET"
            "   statut=excluded.statut, verdict='echec', commentaire=excluded.commentaire,"
            "   maj_le=excluded.maj_le",
            (etudiant, session, numero, STATUT_ECHEC, motif[:1000], _maintenant()))


def sortie_validee(chemin: pathlib.Path, etudiant: str, session: str, numero: int) -> dict | None:
    """Sortie RÉELLE d'une étape validée — c'est elle qui part vers l'étape suivante."""
    ligne = statut(chemin, etudiant, session, numero)
    if not ligne or ligne["statut"] != STATUT_VALIDEE or not ligne["resultat"]:
        return None
    try:
        return json.loads(ligne["resultat"])
    except (TypeError, ValueError):
        return None


def sortie_proposee(chemin: pathlib.Path, etudiant: str, session: str, numero: int) -> dict | None:
    """Dernière sortie enregistrée pour une étape, quel que soit son statut (pour l'affichage)."""
    ligne = statut(chemin, etudiant, session, numero)
    if not ligne or not ligne["resultat"]:
        return None
    try:
        return json.loads(ligne["resultat"])
    except (TypeError, ValueError):
        return None


def quota_du_jour(chemin: pathlib.Path, etudiant: str, jour: str) -> int:
    with _base(chemin) as base:
        ligne = base.execute("SELECT analyses FROM quota WHERE etudiant = ? AND jour = ?",
                             (etudiant, jour)).fetchone()
    return int(ligne["analyses"]) if ligne else 0


def incrementer_quota(chemin: pathlib.Path, etudiant: str, jour: str) -> int:
    with _base(chemin) as base:
        base.execute(
            "INSERT INTO quota (etudiant, jour, analyses) VALUES (?, ?, 1)"
            " ON CONFLICT(etudiant, jour) DO UPDATE SET analyses = analyses + 1",
            (etudiant, jour))
        ligne = base.execute("SELECT analyses FROM quota WHERE etudiant = ? AND jour = ?",
                             (etudiant, jour)).fetchone()
    return int(ligne["analyses"]) if ligne else 0


def journal(chemin: pathlib.Path, etudiant: str, session: str) -> list[dict]:
    """Vue lisible du dossier : toutes les étapes connues, dans l'ordre."""
    with _base(chemin) as base:
        lignes = base.execute(
            "SELECT numero, statut, verdict, decision, maj_le FROM etapes"
            " WHERE etudiant = ? AND session = ? ORDER BY numero",
            (etudiant, session)).fetchall()
    return [dict(ligne) for ligne in lignes]
