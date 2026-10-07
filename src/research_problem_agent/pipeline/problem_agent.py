"""Agent Problème : prépare les appels LLM (phase 1 puis phase 2) et rend le texte brut.

Aucune sortie n'est utilisée en l'état : tout passe ensuite par Parser → Schéma → Métier →
Sécurité (SPEC §10.12).
"""

from pathlib import Path

from ..schemas.input import ProblemRequest

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_phase1_system() -> str:
    return (_PROMPT_DIR / "problem_phase1_system.md").read_text(encoding="utf-8")


def load_phase2_system() -> str:
    return (_PROMPT_DIR / "problem_phase2_system.md").read_text(encoding="utf-8")


def _message(request: ProblemRequest, annotations: list[dict], sources_block: str,
             extra_instruction: str) -> str:
    from .security_layer import build_user_message

    user = build_user_message(request, annotations, sources_block)
    if extra_instruction:
        user = user + "\n\n[INSTRUCTION DE CORRECTION]\n" + extra_instruction
    return user


def phase1(llm, system_prompt: str, request: ProblemRequest, annotations: list[dict],
           extra_instruction: str = "") -> str:
    """Première passe : analyse du sujet + intentions de recherche. Aucune source fournie."""
    return llm.complete(system_prompt, _message(request, annotations, "", extra_instruction))


def phase2(llm, system_prompt: str, request: ProblemRequest, annotations: list[dict],
           sources_block: str, extra_instruction: str = "") -> str:
    """Seconde passe : formulation du problème ancrée sur les sources RÉELLEMENT récupérées."""
    return llm.complete(system_prompt, _message(request, annotations, sources_block,
                                               extra_instruction))
