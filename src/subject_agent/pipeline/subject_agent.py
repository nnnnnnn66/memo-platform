"""Agent Sujet : prépare l'appel LLM et retourne le texte brut (non validé)."""

from pathlib import Path

from ..schemas.input import SubjectRequest

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_subject_system() -> str:
    return (_PROMPT_DIR / "subject_system.md").read_text(encoding="utf-8")


def produce(llm, system_prompt: str, request: SubjectRequest, annotations: list[dict],
            extra_instruction: str = "", sources_bloc: str = "") -> str:
    """Appelle le LLM et renvoie le texte brut. Aucune sortie n'est utilisée en l'état.

    `sources_bloc` : les références RÉELLEMENT récupérées par la recherche documentaire. Elles sont
    placées AVANT l'instruction de correction (une correction porte sur la sortie, pas sur les
    données) et le modèle n'a le droit de citer qu'elles.
    """
    from .security_layer import build_user_message

    user = build_user_message(request, annotations)
    if sources_bloc:
        user = user + "\n\n" + sources_bloc
    if extra_instruction:
        user = user + "\n\n[INSTRUCTION DE CORRECTION]\n" + extra_instruction
    return llm.complete(system_prompt, user)
