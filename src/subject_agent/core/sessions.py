"""Isolation des sessions (SPEC §31).

Toute opération porte student_id + session_id + agent_id.
Aucune fonction ici ne lit les données d'un autre étudiant.
"""

import pathlib
import uuid

AGENT_ID = "subject_agent"


def new_session_id() -> str:
    return str(uuid.uuid4())


def session_dir(workspace_root, student_id: str, session_id: str):
    """Chemin isolé par étudiant puis session. Empêche toute fuite croisée."""
    racine = pathlib.Path(workspace_root).resolve()
    chemin = (racine / _sanitize(student_id) / _sanitize(session_id)).resolve()
    if chemin != racine and racine not in chemin.parents:
        raise ValueError("chemin de session en dehors de l'espace de travail de l'agent")
    return chemin


def _sanitize(value: str) -> str:
    """Ne conserve que des caractères sûrs pour un nom de dossier."""
    keep = [c for c in str(value) if c.isalnum() or c in "-_."]
    out = "".join(keep)[:64]
    return out or "unknown"
