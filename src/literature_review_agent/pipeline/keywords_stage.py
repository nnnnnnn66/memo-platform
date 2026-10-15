"""Phase 1 : concepts, mots-clés et stratégie de recherche (SPEC §9.1–9.3)."""

from pathlib import Path

from ..core.logging import get_logger

log = get_logger("litterature.keywords")
from ..core.errors import ErrorState, PipelineError
from . import output_parser, schema_validation, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p1_keywords_system.md").read_text(encoding="utf-8")


def run(llm, request, annotations: list[dict], limits, extra: str = "",
        max_attempts: int = 2):
    """Produit et valide les mots-clés et la stratégie. Retourne (keywords, attempts)."""
    system = load_system()
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        user = security_layer.build_user_message(request, annotations)
        if extra:
            user += "\n\n[INSTRUCTION DE CORRECTION]\n" + extra
        try:
            raw = llm.complete(system, user)
            data = output_parser.extract_json(raw)
            keywords = schema_validation.validate_keywords(data)
        except PipelineError as exc:
            if attempts < max_attempts:
                extra = (f"Ta sortie précédente était invalide ({exc.state.value}). "
                         f"Détail : {exc.detail[:600]}\nRéémets UNIQUEMENT le JSON conforme.")
                continue
            raise

        # Le modèle propose parfois PLUS de requêtes que la borne de l'agent. On ne fait pas
        # échouer la campagne pour autant : leçon du projet — corriger la surévaluation par le CODE,
        # pas par un échec. On garde les premières (dans l'ordre voulu par le modèle) et on le
        # DÉCLARE. Sans cela, une campagne entière mourait sur « trop de requêtes (9 > 8) ».
        if not keywords.subject_is_too_broad and len(keywords.queries) > limits.max_search_queries:
            retirees = len(keywords.queries) - limits.max_search_queries
            keywords.queries = keywords.queries[:limits.max_search_queries]
            log.info("phase 1 : %s requête(s) au-delà de la borne (%s) retirée(s) ; borne respectée",
                     retirees, limits.max_search_queries)

        violations = []
        if keywords.subject_reference.original.strip() != request.subject_text.strip():
            violations.append("subject_reference.original doit être la copie EXACTE du sujet reçu")
        if not keywords.subject_is_too_broad:
            if not keywords.concepts:
                violations.append("aucun concept identifié")
            if not keywords.queries:
                violations.append("aucune requête de recherche proposée")
            if len(keywords.queries) > limits.max_search_queries:
                violations.append(
                    f"trop de requêtes ({len(keywords.queries)} > {limits.max_search_queries})"
                )
            bad = [q.query for q in keywords.queries if len((q.query or "").split()) < 2]
            if bad:
                violations.append(f"requêtes trop courtes (1 mot) : {bad[:3]}")
        else:
            if not keywords.clarification_questions:
                violations.append("sujet jugé trop vaste mais aucune question de clarification")
        if violations:
            if attempts < max_attempts:
                extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                         + "\n".join(f"- {v}" for v in violations))
                continue
            raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                                "phase 1 non conforme : " + " ; ".join(violations))
        return keywords, attempts
    raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "phase 1 : échec après re-tentatives")
