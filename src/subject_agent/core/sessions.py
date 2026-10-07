"""Isolation des sessions (SPEC §31).

Toute opération porte student_id + session_id + agent_id.
Aucune fonction ici ne lit les données d'un autre étudiant.
"""

import uuid

AGENT_ID = "subject_agent"


def new_session_id() -> str:
    return str(uuid.uuid4())


def session_dir(workspace_root, student_id: str, session_id: str):
    """Chemin isolé par étudiant puis session. Empêche toute fuite croisée."""
    safe_student = _sanitize(student_id)
    safe_session = _sanitize(session_id)
    return workspace_root / safe_student / safe_session


def _sanitize(value: str) -> str:
    """Ne conserve que des caractères sûrs pour un nom de dossier."""
    keep = [c for c in str(value) if c.isalnum() or c in "-_."]
    out = "".join(keep)[:64]
    return out or "unknown"
