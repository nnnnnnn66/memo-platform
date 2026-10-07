"""Phase 4 : diagnostic méthodologique et alignement épistémologique (SPEC §4.4A)."""

from pathlib import Path

from ..core.errors import ErrorState, PipelineError
from ..diagnosis import matrix
from . import output_parser, schema_validation, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p4_diagnosis_system.md").read_text(encoding="utf-8")


def _matrix_block() -> str:
    lines = ["Matrice décisionnelle d'alignement théorique (référence, à utiliser telle quelle) :"]
    for row in matrix.MATRIX:
        lines.append(
            f"- {row.id} | {row.label} | indicateurs : {', '.join(row.indicators)} | "
            f"logique : {row.reasoning_logic} | type : {row.research_type} | "
            f"approche : {row.approach} | techniques : {', '.join(row.techniques)}"
        )
    return "\n".join(lines)


def _knowledge_block(synthesis, records) -> str:
    themes = "\n".join(
        f"- {theme.theme} ({len(theme.doc_ids)} documents) : "
        f"convergences={theme.convergences[:2]} limites={theme.limits[:2]} lacunes={theme.gaps[:2]}"
        for theme in synthesis.comparison.themes
    )
    methods = ", ".join(synthesis.comparison.methods_used[:12])
    return (
        "État des connaissances établi sur le corpus (données) :\n"
        f"{themes}\nMéthodes observées : {methods or 'aucune méthode identifiée'}\n"
        f"Angles morts : {'; '.join(synthesis.synthesis.blind_spots[:5]) or 'aucun signalé'}\n"
        f"Corpus : {len(records)} documents retenus."
    )


def run(llm, request, synthesis, records, annotations: list[dict], settings, extra: str = "",
        max_attempts: int = 2):
    """Produit et valide le diagnostic. Retourne (diagnosis, attempts)."""
    system = load_system()
    blocks = [_matrix_block(), _knowledge_block(synthesis, records)]
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        user = security_layer.build_user_message(request, annotations, blocks)
        if extra:
            user += "\n\n[INSTRUCTION DE CORRECTION]\n" + extra
        try:
            raw = llm.complete(system, user)
            data = output_parser.extract_json(raw)
            diagnosis = schema_validation.validate_diagnosis(data)
        except PipelineError as exc:
            if attempts < max_attempts:
                extra = (f"Ta sortie précédente était invalide ({exc.state.value}). "
                         f"Détail : {exc.detail[:500]}\nRéémets uniquement le JSON conforme.")
                continue
            raise

        violations = []
        if settings.diagnosis.get("require_matrix_row", True) and diagnosis.matrix_row_id not in matrix.BY_ID:
            violations.append(
                f"matrix_row_id « {diagnosis.matrix_row_id} » absent de la matrice fournie "
                f"(valeurs possibles : {', '.join(matrix.BY_ID)})"
            )
        elif diagnosis.matrix_row_id in matrix.BY_ID:
            issues = matrix.row_coherence_issues(
                diagnosis.matrix_row_id, diagnosis.reasoning_logic.value,
                diagnosis.research_type.value, diagnosis.approach.value, diagnosis.techniques)
            # Une incohérence est signalée au modèle ; si elle persiste, elle est conservée comme
            # alerte d'alignement (le diagnostic reste une proposition) plutôt que bloquante.
            if issues and not diagnosis.alignment_alerts:
                violations.append(
                    "incohérence de matrice non signalée : " + " ; ".join(issues)
                    + " → ajoute-la dans alignment_alerts ou corrige la démarche"
                )
        if not diagnosis.justification.strip():
            violations.append("justification vide")
        if violations:
            if attempts < max_attempts:
                extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                         + "\n".join(f"- {v}" for v in violations))
                continue
            raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                                "phase 4 non conforme : " + " ; ".join(violations))
        return diagnosis, attempts
    raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "phase 4 : échec après re-tentatives")
