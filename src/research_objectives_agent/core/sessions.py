"""Isolation des sessions par étudiant (SPEC §6, §11)."""

import pathlib
import re
import uuid

AGENT_ID = "research_objectives_agent"


def new_session_id() -> str:
    return str(uuid.uuid4())


def session_dir(workspace_root, student_id: str, session_id: str):
    """Chemin isolé par étudiant puis session. Empêche toute fuite croisée.

    DOUBLE BARRIÈRE (alerte py/path-injection de CodeQL) :
    1. l'assainissement ci-dessous retire tout caractère dangereux et neutralise « .. » ;
    2. le chemin RÉSOLU est ensuite vérifié comme réellement contenu dans l'espace de travail.
    La seconde barrière est volontairement redondante : elle protège même si l'assainissement
    changeait un jour, et elle est visible par l'analyseur statique (qui ne peut pas suivre une
    fonction d'assainissement écrite maison).
    """
    racine = pathlib.Path(workspace_root).resolve()
    chemin = (racine / _sanitize(student_id) / _sanitize(session_id)).resolve()
    if chemin != racine and racine not in chemin.parents:
        raise ValueError("chemin de session en dehors de l'espace de travail de l'agent")
    return chemin


def _sanitize(value: str) -> str:
    """Ne conserve que des caractères sûrs ; neutralise « .. » (pas de remontée de chemin)."""
    keep = [c for c in str(value) if c.isalnum() or c in "-_. "]
    out = "".join(keep)[:64].strip()
    out = re.sub(r"\.{2,}", ".", out).strip(".")
    return out or "unknown"
