"""Artefacts de session, isolés par étudiant."""

import json
from pathlib import Path

from ..core.sessions import session_dir


def save(workspace_root: Path, student_id: str, session_id: str, name: str, payload) -> Path:
    directory = session_dir(workspace_root, student_id, session_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(workspace_root: Path, student_id: str, session_id: str, name: str):
    path = session_dir(workspace_root, student_id, session_id) / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
