"""Applique la décision de l'étudiant sur la sortie RÉELLE de l'agent 11 (portillon humain).

Usage : set -a; . ~/.hermes/.env; set +a; PYTHONPATH=src .venv/bin/python scripts/decision_agent11.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

from research_conclusion_agent.core.config import get_settings  # noqa: E402
from research_conclusion_agent.llm.client import LLMClient  # noqa: E402
from research_conclusion_agent.pipeline import campaign  # noqa: E402
from research_conclusion_agent.schemas.decision import (  # noqa: E402
    DecisionRequest,
    DecisionValue,
)
from research_conclusion_agent.schemas.input import ConclusionRequest  # noqa: E402
from research_conclusion_agent.schemas.output import ConclusionOutput  # noqa: E402


def load(stage: int):
    return json.loads((ROOT / f"workspace/chaine-live/stage{stage}.json").read_text())["output"]


results_up = dict(load(10))
results_up.setdefault("student_validation", {"decision": "accepted", "comment": ""})
methodology = dict(load(9))
methodology.setdefault("student_validation", {"decision": "accepted", "comment": ""})

request = ConclusionRequest(
    student_id="chaine-etu", session_id="chaine-live",
    subject_text="Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
    discipline="Sciences de gestion", academic_level="Master 2",
    upstream_question=load(5), upstream_objectives=load(6), upstream_hypotheses=load(7),
    upstream_methodology=methodology, upstream_results=results_up)

settings = get_settings()
llm = LLMClient(settings.llm_credentials(), settings.limits)
output = ConclusionOutput.model_validate(json.loads(
    (ROOT / "workspace/chaine-live/stage11.json").read_text())["output"])
print("avant décision :", output.status.value, "|", output.document_status.value)

result = campaign.decide(request, settings, llm, output,
                        DecisionRequest(decision=DecisionValue.accepted,
                                        student_comment="conclusion acceptée après relecture"))
print("après décision :", result.output.status.value, "|", result.output.document_status.value)
print("décision étudiante :", result.output.student_validation.decision)
print("confiance :", result.output.confidence.overall)
print("calcul     :", result.output.confidence.rationale)
print("versions   :", result.output.historique_versions)
