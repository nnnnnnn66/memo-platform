"""Applique la décision de l'étudiant sur la sortie RÉELLE de l'agent 9 (portillon humain).

Usage : set -a; . ~/.hermes/.env; set +a; PYTHONPATH=src .venv/bin/python scripts/decision_agent9.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

from methodology_agent.core.config import get_settings  # noqa: E402
from methodology_agent.llm.client import LLMClient  # noqa: E402
from methodology_agent.pipeline import campaign  # noqa: E402
from methodology_agent.schemas.decision import DecisionRequest, DecisionValue  # noqa: E402
from methodology_agent.schemas.input import MethodologyRequest  # noqa: E402
from methodology_agent.schemas.output import MethodologyOutput  # noqa: E402


def load(stage: int):
    return json.loads((ROOT / f"workspace/chaine-live/stage{stage}.json").read_text())["output"]


diagnostic = dict(load(8))
diagnostic.setdefault("student_validation", {"decision": "accepted", "comment": ""})

request = MethodologyRequest(
    student_id="chaine-etu", session_id="chaine-live",
    subject_text="Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
    discipline="Sciences de gestion", academic_level="Master 2",
    country="Côte d'Ivoire", geographical_area="Abidjan", study_period="2020-2024",
    target_population="développeurs",
    field_access="Enquête de terrain possible auprès des entreprises de services numériques.",
    available_data="Questionnaires et entretiens à réaliser auprès des développeurs.",
    available_resources="Six mois de terrain, budget limité.",
    upstream_methodology_diagnostic=diagnostic,
    upstream_question=load(5), upstream_objectives=load(6), upstream_hypotheses=load(7))

settings = get_settings()
llm = LLMClient(settings.llm_credentials(), settings.limits)
output = MethodologyOutput.model_validate(json.loads(
    (ROOT / "workspace/chaine-live/stage9.json").read_text())["output"])
print("avant décision :", output.status.value, "|", output.document_status.value)

result = campaign.decide(request, settings, llm, output,
                        DecisionRequest(decision=DecisionValue.accepted,
                                        student_comment="protocole accepté après relecture"))
print("après décision :", result.output.status.value, "|", result.output.document_status.value)
print("décision étudiante :", result.output.student_validation.decision)
print("confiance :", result.output.confidence.overall)
print("calcul     :", result.output.confidence.rationale)
