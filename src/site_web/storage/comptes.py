"""Comptes, invitations, sessions et journal du site (SQLite de la bibliothèque standard).

Ce fichier ne contient AUCUNE donnée méthodologique : les mémoires appartiennent à
l'orchestrateur. Ici, seulement qui peut entrer et ce qui s'est passé côté site.
"""

import datetime
import pathlib
import sqlite3
from contextlib import contextmanager

from ..core.securite import jeton as _nouveau_jeton

SCHEMA = """
CREATE TABLE IF NOT EXISTS invitations (
    jeton       TEXT PRIMARY KEY,
    email       TEXT NOT NULL DEFAULT '',
    cree_le     TEXT NOT NULL,
    utilise_le  TEXT
);
CREATE TABLE IF NOT EXISTS comptes (
    identifiant  TEXT PRIMARY KEY,
    email        TEXT NOT NULL DEFAULT '',
    empreinte    TEXT NOT NULL,
    cree_le      TEXT NOT NULL,
    est_admin    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
    jeton        TEXT PRIMARY KEY,
    identifiant  TEXT NOT NULL,
    cree_le      TEXT NOT NULL,
    vu_le        TEXT NOT NULL,
    expire_le    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tentatives (
    identifiant  TEXT PRIMARY KEY,
    echecs       INTEGER NOT NULL DEFAULT 0,
    bloque_jusqu TEXT
);
CREATE TABLE IF NOT EXISTS journal_site (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant  TEXT NOT NULL DEFAULT '',
    session_memo TEXT NOT NULL DEFAULT '',
    action       TEXT NOT NULL,
    detail       TEXT NOT NULL DEFAULT '',
    quand        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memoires (
    session      TEXT NOT NULL,
    identifiant  TEXT NOT NULL,
    sujet        TEXT NOT NULL,
    contexte     TEXT NOT NULL DEFAULT '{}',
    cree_le      TEXT NOT NULL,
    PRIMARY KEY (identifiant, session)
);
"""


def _maintenant() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _plus_tard(heures: int = 0, minutes: int = 0) -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=heures, minutes=minutes)).isoformat()


@contextmanager
def _base(chemin: pathlib.Path):
    chemin = pathlib.Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    try:
        connexion.executescript(SCHEMA)
        yield connexion
        connexion.commit()
    finally:
        connexion.close()


# ---------------------------------------------------------------- invitations
def creer_invitation(chemin, jeton: str, email: str = "") -> None:
    with _base(chemin) as base:
        base.execute("INSERT OR REPLACE INTO invitations (jeton, email, cree_le, utilise_le)"
                     " VALUES (?, ?, ?, NULL)", (jeton, email, _maintenant()))


def invitation_valide(chemin, jeton: str) -> bool:
    with _base(chemin) as base:
        ligne = base.execute("SELECT utilise_le FROM invitations WHERE jeton = ?",
                             (jeton,)).fetchone()
    return bool(ligne) and not ligne["utilise_le"]


def consommer_invitation(chemin, jeton: str) -> None:
    with _base(chemin) as base:
        base.execute("UPDATE invitations SET utilise_le = ? WHERE jeton = ?",
                     (_maintenant(), jeton))


# -------------------------------------------------------------------- comptes
def identifiant_libre(chemin, identifiant: str) -> bool:
    with _base(chemin) as base:
        ligne = base.execute("SELECT 1 FROM comptes WHERE identifiant = ?",
                             (identifiant,)).fetchone()
    return ligne is None


def creer_compte(chemin, identifiant: str, empreinte: str, email: str = "",
                 est_admin: bool = False) -> None:
    with _base(chemin) as base:
        base.execute("INSERT INTO comptes (identifiant, email, empreinte, cree_le, est_admin)"
                     " VALUES (?, ?, ?, ?, ?)",
                     (identifiant, email, empreinte, _maintenant(), 1 if est_admin else 0))


def empreinte_de(chemin, identifiant: str) -> str | None:
    with _base(chemin) as base:
        ligne = base.execute("SELECT empreinte FROM comptes WHERE identifiant = ?",
                             (identifiant,)).fetchone()
    return ligne["empreinte"] if ligne else None


def compte(chemin, identifiant: str) -> dict | None:
    with _base(chemin) as base:
        ligne = base.execute("SELECT * FROM comptes WHERE identifiant = ?",
                             (identifiant,)).fetchone()
    return dict(ligne) if ligne else None


def nombre_comptes(chemin) -> int:
    with _base(chemin) as base:
        return int(base.execute("SELECT COUNT(*) AS n FROM comptes").fetchone()["n"])


# ------------------------------------------------------------------- sessions
def ouvrir_session(chemin, identifiant: str, duree_heures: int) -> str:
    jeton = _nouveau_jeton()
    with _base(chemin) as base:
        base.execute("INSERT INTO sessions (jeton, identifiant, cree_le, vu_le, expire_le)"
                     " VALUES (?, ?, ?, ?, ?)",
                     (jeton, identifiant, _maintenant(), _maintenant(),
                      _plus_tard(heures=duree_heures)))
    return jeton


def session_valide(chemin, jeton: str) -> str | None:
    """Renvoie l'identifiant si la session est valide, sinon None. La session est rafraîchie."""
    if not jeton:
        return None
    with _base(chemin) as base:
        ligne = base.execute("SELECT * FROM sessions WHERE jeton = ?", (jeton,)).fetchone()
        if not ligne:
            return None
        if ligne["expire_le"] < _maintenant():
            base.execute("DELETE FROM sessions WHERE jeton = ?", (jeton,))
            return None
        base.execute("UPDATE sessions SET vu_le = ? WHERE jeton = ?", (_maintenant(), jeton))
        return ligne["identifiant"]


def fermer_session(chemin, jeton: str) -> None:
    with _base(chemin) as base:
        base.execute("DELETE FROM sessions WHERE jeton = ?", (jeton,))


# --------------------------------------------------- tentatives de connexion
def est_bloque(chemin, identifiant: str) -> int:
    """Renvoie le nombre de minutes de blocage restantes (0 si l'accès est libre)."""
    with _base(chemin) as base:
        ligne = base.execute("SELECT bloque_jusqu FROM tentatives WHERE identifiant = ?",
                             (identifiant,)).fetchone()
    if not ligne or not ligne["bloque_jusqu"]:
        return 0
    reste = (datetime.datetime.fromisoformat(ligne["bloque_jusqu"])
             - datetime.datetime.now(datetime.timezone.utc))
    return max(0, int(reste.total_seconds() // 60) + (1 if reste.total_seconds() > 0 else 0))


def enregistrer_echec(chemin, identifiant: str, maximum: int, blocage_minutes: int) -> int:
    with _base(chemin) as base:
        ligne = base.execute("SELECT echecs FROM tentatives WHERE identifiant = ?",
                             (identifiant,)).fetchone()
        echecs = (ligne["echecs"] if ligne else 0) + 1
        blocage = None
        if echecs >= maximum:
            blocage = _plus_tard(minutes=blocage_minutes)
            echecs = 0
        base.execute("INSERT INTO tentatives (identifiant, echecs, bloque_jusqu)"
                     " VALUES (?, ?, ?)"
                     " ON CONFLICT(identifiant) DO UPDATE SET"
                     " echecs=excluded.echecs, bloque_jusqu=excluded.bloque_jusqu",
                     (identifiant, echecs, blocage))
    return 0 if blocage is None else blocage_minutes


def reinitialiser_tentatives(chemin, identifiant: str) -> None:
    with _base(chemin) as base:
        base.execute("DELETE FROM tentatives WHERE identifiant = ?", (identifiant,))


# -------------------------------------------------------------------- journal
def consigner(chemin, action: str, identifiant: str = "", session_memo: str = "",
              detail: str = "") -> None:
    with _base(chemin) as base:
        base.execute("INSERT INTO journal_site (identifiant, session_memo, action, detail, quand)"
                     " VALUES (?, ?, ?, ?, ?)",
                     (identifiant, session_memo, action, detail[:500], _maintenant()))


def journal(chemin, identifiant: str = "", limite: int = 60) -> list:
    with _base(chemin) as base:
        if identifiant:
            lignes = base.execute(
                "SELECT * FROM journal_site WHERE identifiant = ? ORDER BY id DESC LIMIT ?",
                (identifiant, limite)).fetchall()
        else:
            lignes = base.execute(
                "SELECT * FROM journal_site ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(ligne) for ligne in lignes]


def invitations_ouvertes(chemin) -> list:
    with _base(chemin) as base:
        lignes = base.execute("SELECT * FROM invitations ORDER BY cree_le DESC LIMIT 50").fetchall()
    return [dict(ligne) for ligne in lignes]


# ------------------------------------------------------------------ mémoires
# L'index des mémoires appartient au SITE (quel étudiant a quel mémoire) ; le CONTENU
# méthodologique appartient à l'orchestrateur. Cette table ne duplique aucun dossier.
def creer_memoire(chemin, identifiant: str, session: str, sujet: str, contexte: str = "{}") -> None:
    with _base(chemin) as base:
        base.execute("INSERT OR IGNORE INTO memoires (session, identifiant, sujet, contexte, cree_le)"
                     " VALUES (?, ?, ?, ?, ?)",
                     (session, identifiant, sujet, contexte, _maintenant()))


def mes_memoires(chemin, identifiant: str) -> list:
    with _base(chemin) as base:
        lignes = base.execute("SELECT * FROM memoires WHERE identifiant = ? ORDER BY cree_le DESC",
                              (identifiant,)).fetchall()
    return [dict(ligne) for ligne in lignes]


def mon_memoire(chemin, identifiant: str, session: str) -> dict | None:
    """Le mémoire appartient-il bien à cet étudiant ? (isolation, vérifiée à chaque page)."""
    with _base(chemin) as base:
        ligne = base.execute("SELECT * FROM memoires WHERE identifiant = ? AND session = ?",
                             (identifiant, session)).fetchone()
    return dict(ligne) if ligne else None
