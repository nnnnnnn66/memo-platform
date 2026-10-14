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
-- Journal des REPRISES : une étape déjà franchie que l'étudiant rouvre.
-- Table APPEND-ONLY et c'est voulu : `enregistrer_resultat` remet `decision` et `commentaire` à zéro
-- lors du nouveau passage ; sans ce journal, la décision antérieure de l'étudiant disparaîtrait
-- sans laisser de trace. On y consigne l'état AVANT reprise (statut, verdict, décision,
-- commentaire) et la liste des étapes aval invalidées du fait de la reprise.
CREATE TABLE IF NOT EXISTS reprises (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    etudiant           TEXT NOT NULL,
    session            TEXT NOT NULL,
    numero             INTEGER NOT NULL,
    ancien_statut      TEXT NOT NULL DEFAULT '',
    ancien_verdict     TEXT NOT NULL DEFAULT '',
    ancienne_decision  TEXT NOT NULL DEFAULT '',
    ancien_commentaire TEXT NOT NULL DEFAULT '',
    aval               TEXT NOT NULL DEFAULT '[]',
    motif              TEXT NOT NULL DEFAULT '',
    maj_le             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS reprises_dossier ON reprises (etudiant, session, numero);
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
        # Nombre de fois que chaque étape a été REPRISE : l'étudiant doit pouvoir voir qu'une étape
        # n'est pas « neuve » sans que cela change son statut courant.
        compte = {int(ligne["numero"]): int(ligne["n"]) for ligne in base.execute(
            "SELECT numero, COUNT(*) AS n FROM reprises"
            " WHERE etudiant = ? AND session = ? GROUP BY numero",
            (etudiant, session)).fetchall()}
    return [{**dict(ligne), "reprises": compte.get(int(ligne["numero"]), 0)}
            for ligne in lignes]


# ============================================================================
# REPRENDRE UNE ÉTAPE DÉJÀ FRANCHIE
# ============================================================================
# Une étape validée est franchie : le parcours est passé à la suivante. Jusqu'ici, revenir dessus
# était IMPOSSIBLE sans intervenir directement dans la base — or un mémoire est itératif : l'étudiant
# reçoit de nouvelles données, ou veut corriger. Ces fonctions rendent la reprise possible sans
# casser la règle qui fonde la qualité de la plateforme : on n'avance jamais sur une production non
# vérifiée.

def rouvrir(chemin: pathlib.Path, etudiant: str, session: str, numero: int) -> None:
    """Repasse une étape franchie à `a_faire` : elle redevient l'étape ouverte.

    La `decision` et le `commentaire` sont remis à zéro — la nouvelle tentative repart d'une feuille
    nette — mais l'état antérieur a été journalisé AVANT (voir `enregistrer_reprise`) : rien ne se
    perd. Le `resultat` antérieur est CONSERVÉ pour rester lisible pendant la reprise ; il sera
    remplacé par la nouvelle production au prochain `enregistrer_resultat`.
    """
    with _base(chemin) as base:
        base.execute(
            "UPDATE etapes SET statut = ?, decision = '', commentaire = '', maj_le = ?"
            " WHERE etudiant = ? AND session = ? AND numero = ?",
            (STATUT_A_FAIRE, _maintenant(), etudiant, session, numero))
        base.execute("UPDATE dossiers SET maj_le = ? WHERE etudiant = ? AND session = ?",
                     (_maintenant(), etudiant, session))


def marquer_a_reviser(chemin: pathlib.Path, etudiant: str, session: str, numero: int) -> str:
    """Retire à une étape son statut « validée » sans effacer sa production.

    C'est ainsi que l'orchestrateur refuse de LAISSER MENTIR une étape aval : son contenu reste
    lisible, mais son statut dit qu'elle doit être revue. Comme `sortie_validee` n'accepte que le
    statut `validee`, plus rien ne peut s'appuyer dessus en silence.
    """
    with _base(chemin) as base:
        base.execute(
            "UPDATE etapes SET statut = ?, maj_le = ?"
            " WHERE etudiant = ? AND session = ? AND numero = ?",
            (STATUT_A_REVISER, _maintenant(), etudiant, session, numero))
        base.execute("UPDATE dossiers SET maj_le = ? WHERE etudiant = ? AND session = ?",
                     (_maintenant(), etudiant, session))
    return STATUT_A_REVISER


def enregistrer_reprise(chemin: pathlib.Path, etudiant: str, session: str, numero: int,
                        ancien: dict, aval: list[int], motif: str = "") -> None:
    """Journalise la reprise : l'état AVANT (statut, verdict, décision, commentaire) et les étapes
    aval invalidées. Les décisions déjà prises restent ainsi traçables, même lorsque la ligne de
    `etapes` est réécrite par le nouveau passage."""
    with _base(chemin) as base:
        base.execute(
            "INSERT INTO reprises (etudiant, session, numero, ancien_statut, ancien_verdict,"
            " ancienne_decision, ancien_commentaire, aval, motif, maj_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (etudiant, session, numero, str(ancien.get("statut", "")),
             str(ancien.get("verdict", "")), str(ancien.get("decision", "")),
             str(ancien.get("commentaire", "")),
             json.dumps([int(n) for n in aval], ensure_ascii=False), motif, _maintenant()))


def reprises(chemin: pathlib.Path, etudiant: str, session: str,
             numero: int | None = None) -> list[dict]:
    """Le journal des reprises, du plus récent au plus ancien (toutes étapes, ou une seule)."""
    requete = ("SELECT id, numero, ancien_statut, ancien_verdict, ancienne_decision,"
               " ancien_commentaire, aval, motif, maj_le FROM reprises"
               " WHERE etudiant = ? AND session = ?")
    parametres: list = [etudiant, session]
    if numero is not None:
        requete += " AND numero = ?"
        parametres.append(int(numero))
    requete += " ORDER BY id DESC"
    with _base(chemin) as base:
        lignes = base.execute(requete, parametres).fetchall()
    resultat = []
    for ligne in lignes:
        item = dict(ligne)
        try:
            item["aval"] = json.loads(item.get("aval") or "[]")
        except (TypeError, ValueError):
            item["aval"] = []
        resultat.append(item)
    return resultat
