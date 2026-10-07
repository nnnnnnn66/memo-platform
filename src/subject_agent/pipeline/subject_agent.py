"""Agent Sujet : prépare l'appel LLM et retourne le texte brut (non validé)."""

from pathlib import Path

from ..schemas.input import SubjectRequest

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_subject_system() -> str:
    return (_PROMPT_DIR / "subject_system.md").read_text(encoding="utf-8")


def produce(llm, system_prompt: str, request: SubjectRequest, annotations: list[dict],
            extra_instruction: str = "") -> str:
    """Appelle le LLM et renvoie le texte brut. Aucune sortie n'est utilisée en l'état."""
    from .security_layer import build_user_message

    user = build_user_message(request, annotations)
    if extra_instruction:
        user = user + "\n\n[INSTRUCTION DE CORRECTION]\n" + extra_instruction
    return llm.complete(system_prompt, user)
