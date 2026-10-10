"""Applique la décision de l'étudiant sur la sortie RÉELLE de l'Agent 13 (portillon humain).

Usage : set -a; . ~/.hermes/.env; set +a; PYTHONPATH=src .venv/bin/python scripts/decision_agent13.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

from research_coherence_verifier.core.config import get_settings  # noqa: E402
from research_coherence_verifier.llm.client import LLMClient  # noqa: E402
from research_coherence_verifier.pipeline import campaign  # noqa: E402
from research_coherence_verifier.schemas.decision import (  # noqa: E402
    DecisionRequest,
    DecisionValue,
)
from research_coherence_verifier.schemas.input import CoherenceRequest  # noqa: E402
from research_coherence_verifier.schemas.output import CoherenceOutput  # noqa: E402

CHAINE = ROOT / "workspace" / "chaine-live"


def load(stage: int) -> dict:
    return json.loads((CHAINE / f"stage{stage}.json").read_text(encoding="utf-8"))["output"]


request = CoherenceRequest(
    student_id="chaine-etu", session_id="chaine-live", discipline="Sciences de gestion",
    academic_level="Master 2",
    upstream_subject=load(1), upstream_problem=load(2), upstream_literature=load(3),
    upstream_problematic=load(4), upstream_question=load(5), upstream_objectives=load(6),
    upstream_hypotheses=load(7), upstream_methodology_diagnostic=load(8),
    upstream_methodology=load(9), upstream_results=load(10), upstream_conclusion=load(11))

settings = get_settings()
llm = LLMClient(settings.llm_credentials(), settings.limits)
output = CoherenceOutput.model_validate(
    json.loads((CHAINE / "stage13.json").read_text(encoding="utf-8"))["output"])
print("avant décision :", output.status.value, "|", output.document_status.value,
      "| verdict", output.report.verdict.value)

result = campaign.decide(request, settings, llm, output,
                        DecisionRequest(decision=DecisionValue.accepted,
                                        student_comment="constats pris en compte après relecture"))
print("après décision :", result.output.status.value, "|", result.output.document_status.value)
print("décision étudiante :", result.output.student_validation.decision)
print("verdict :", result.output.report.verdict.value)
print("confiance :", result.output.confidence.overall)
print("calcul    :", result.output.confidence.rationale)
print("versions  :", result.output.historique_versions)
