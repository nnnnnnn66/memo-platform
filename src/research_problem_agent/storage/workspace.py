"""Artefacts de session, isolés par étudiant (SPEC §11 : write = workspace_only)."""

import json
from pathlib import Path

from ..core.sessions import session_dir


def save(workspace_root: Path, student_id: str, session_id: str, name: str, payload) -> Path:
    directory = session_dir(workspace_root, student_id, session_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = _dans_la_base(directory, directory / f"{name}.json")
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(workspace_root: Path, student_id: str, session_id: str, name: str):
    path = _dans_la_base(session_dir(workspace_root, student_id, session_id),
                         session_dir(workspace_root, student_id, session_id) / f"{name}.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _dans_la_base(base: Path, chemin: Path) -> Path:
    """Vérifie que `chemin` reste DANS `base`, une fois les deux résolus.

    Troisième barrière, après l'assainissement des identifiants et la vérification faite dans
    `session_dir`. Elle est écrite de la façon que l'analyse statique (CodeQL, règle
    py/path-injection) reconnaît comme une garantie : elle ne sait pas suivre une fonction
    d'assainissement écrite maison, mais elle reconnaît `is_relative_to`.
    """
    base = base.resolve()
    chemin = chemin.resolve()
    if chemin != base and not chemin.is_relative_to(base):
        raise ValueError("chemin en dehors de l'espace de travail de l'agent")
    return chemin
