"""Applique la décision de l'étudiant sur la sortie RÉELLE de l'agent 10 (portillon humain).

Usage : set -a; . ~/.hermes/.env; set +a; PYTHONPATH=src .venv/bin/python scripts/decision_agent10.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

from research_results_analysis_agent.core.config import get_settings  # noqa: E402
from research_results_analysis_agent.llm.client import LLMClient  # noqa: E402
from research_results_analysis_agent.pipeline import campaign  # noqa: E402
from research_results_analysis_agent.schemas.decision import (  # noqa: E402
    DecisionRequest,
    DecisionValue,
)
from research_results_analysis_agent.schemas.input import Dataset, ResultsAnalysisRequest  # noqa: E402
from research_results_analysis_agent.schemas.output import ResultsOutput  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from e2e_chaine import DATASET_ETUDIANT  # noqa: E402


def load(stage: int):
    return json.loads((ROOT / f"workspace/chaine-live/stage{stage}.json").read_text())["output"]


methodology = dict(load(9))
methodology.setdefault("student_validation", {"decision": "accepted", "comment": ""})

request = ResultsAnalysisRequest(
    student_id="chaine-etu", session_id="chaine-live",
    subject_text="Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
    discipline="Sciences de gestion", academic_level="Master 2",
    data_origin="Questionnaire administré auprès de développeurs en télétravail.",
    data_period="2024",
    datasets=[Dataset(nom="enquete-developpeurs", format="csv", contenu=DATASET_ETUDIANT,
                      source="Questionnaire administré par l'étudiant", periode="2024")],
    upstream_question=load(5), upstream_objectives=load(6), upstream_hypotheses=load(7),
    upstream_methodology=methodology)

settings = get_settings()
llm = LLMClient(settings.llm_credentials(), settings.limits)
output = ResultsOutput.model_validate(json.loads(
    (ROOT / "workspace/chaine-live/stage10.json").read_text())["output"])
print("avant décision :", output.status.value, "|", output.document_status.value)

result = campaign.decide(request, settings, llm, output,
                        DecisionRequest(decision=DecisionValue.accepted,
                                        student_comment="résultats acceptés après relecture"))
print("après décision :", result.output.status.value, "|", result.output.document_status.value)
print("décision étudiante :", result.output.student_validation.decision)
print("confiance :", result.output.confidence.overall)
print("calcul     :", result.output.confidence.rationale)
