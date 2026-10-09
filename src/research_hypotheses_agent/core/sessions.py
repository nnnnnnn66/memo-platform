"""Isolation des sessions par étudiant (SPEC §6, §11)."""

import re
import uuid

AGENT_ID = "research_hypotheses_agent"


def new_session_id() -> str:
    return str(uuid.uuid4())


def session_dir(workspace_root, student_id: str, session_id: str):
    """Chemin isolé par étudiant puis session. Empêche toute fuite croisée."""
    return workspace_root / _sanitize(student_id) / _sanitize(session_id)


def _sanitize(value: str) -> str:
    """Ne conserve que des caractères sûrs ; neutralise « .. » (pas de remontée de chemin)."""
    keep = [c for c in str(value) if c.isalnum() or c in "-_. "]
    out = "".join(keep)[:64].strip()
    out = re.sub(r"\.{2,}", ".", out).strip(".")
    return out or "unknown"
