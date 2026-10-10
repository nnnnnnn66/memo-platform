"""Sonde : capture la sortie BRUTE du modèle à l'étape 7 (Hypothèses) pour diagnostiquer un JSON
invalide que la re-tentative ne corrige pas.

Usage :
    set -a; . ~/.hermes/.env; set +a
    PYTHONPATH=src .venv/bin/python scripts/probe_agent7.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

from research_hypotheses_agent.core.config import get_settings  # noqa: E402
from research_hypotheses_agent.core.errors import PipelineError  # noqa: E402
from research_hypotheses_agent.llm.client import LLMClient  # noqa: E402
from research_hypotheses_agent.pipeline import campaign  # noqa: E402
from research_hypotheses_agent.schemas.input import HypothesesRequest  # noqa: E402

OUT = pathlib.Path("/root/.hermes/cache/scratch/agent7_brut")
OUT.mkdir(parents=True, exist_ok=True)

stage5 = json.loads((ROOT / "workspace/chaine-live/stage5.json").read_text())["output"]
stage6 = json.loads((ROOT / "workspace/chaine-live/stage6.json").read_text())["output"]


class LoggingLLM:
    """Enveloppe le client réel et conserve chaque réponse brute."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = 0

    def complete(self, system, user):
        raw = self.inner.complete(system, user)
        self.calls += 1
        path = OUT / f"appel{self.calls:02d}.txt"
        path.write_text(f"### SYSTEM\n{system}\n\n### USER\n{user}\n\n### REPONSE\n{raw}",
                        encoding="utf-8")
        print(f"  appel {self.calls} : {len(raw)} caractères -> {path.name}", flush=True)
        return raw


settings = get_settings()
inner = LLMClient(settings.llm_credentials(), settings.limits)
llm = LoggingLLM(inner)

request = HypothesesRequest(
    student_id="chaine-etu", session_id="chaine-live",
    subject_text=stage5.get("subject") if isinstance(stage5.get("subject"), str) else "",
    main_research_question=stage5.get("main_research_question"),
    secondary_research_questions=stage5.get("secondary_research_questions") or [],
    general_objective=stage6.get("general_objective"),
    specific_objectives=stage6.get("specific_objectives") or [],
    discipline="Sciences de gestion", academic_level="Master 2", country="Côte d'Ivoire",
    geographical_area="Abidjan", study_period="2020-2024", target_population="développeurs",
    upstream_subject=json.loads((ROOT / "workspace/chaine-live/stage1.json").read_text())["output"],
    upstream_problem=json.loads((ROOT / "workspace/chaine-live/stage2.json").read_text())["output"],
    upstream_problematic=json.loads(
        (ROOT / "workspace/chaine-live/stage4.json").read_text())["output"],
    upstream_question=stage5, upstream_objectives=stage6)

try:
    result = campaign.run(request, settings, llm, allow_network=False)
    print("statut :", result.output.status.value, "| vérificateur :", result.verifier_status)
except PipelineError as exc:
    print("ÉCHEC :", exc.state.value, "-", exc.detail[:300])

print("\n--- dernières réponses brutes ---")
for path in sorted(OUT.glob("appel*.txt"))[-3:]:
    text = path.read_text(encoding="utf-8").split("### REPONSE", 1)[-1].strip()
    print(f"\n=== {path.name} (fin, 700 derniers caractères) ===")
    print(text[-700:])
