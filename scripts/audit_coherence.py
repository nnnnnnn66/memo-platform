"""Campagne RÉELLE de l'Agent 13 : audit transversal du dossier produit par la chaîne 1 → 11.

Usage :
    set -a; . ~/.hermes/.env; set +a
    PYTHONPATH=src .venv/bin/python -u scripts/audit_coherence.py

Charge les sorties RÉELLES `workspace/chaine-live/stage1..11.json`, exécute l'audit (modèle réel,
réseau désactivé) et écrit `stage13.json`.
"""

import json
import pathlib
import sys
import time

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

CHAINE = ROOT / "workspace" / "chaine-live"


def load(stage: int) -> dict:
    path = CHAINE / f"stage{stage}.json"
    if not path.exists():
        raise SystemExit(f"sortie réelle absente : {path}")
    return json.loads(path.read_text(encoding="utf-8"))["output"]


def main() -> int:
    from research_coherence_verifier.core.config import get_settings
    from research_coherence_verifier.llm.client import LLMClient
    from research_coherence_verifier.pipeline import campaign
    from research_coherence_verifier.schemas.input import CoherenceRequest

    print("=" * 78)
    print("AGENT 13 — VÉRIFICATEUR GLOBAL DE COHÉRENCE — audit du dossier RÉEL 1 → 11")
    print("=" * 78)

    body = CoherenceRequest(
        student_id="chaine-etu", session_id="chaine-live",
        discipline="Sciences de gestion", academic_level="Master 2",
        upstream_subject=load(1), upstream_problem=load(2), upstream_literature=load(3),
        upstream_problematic=load(4), upstream_question=load(5), upstream_objectives=load(6),
        upstream_hypotheses=load(7), upstream_methodology_diagnostic=load(8),
        upstream_methodology=load(9), upstream_results=load(10), upstream_conclusion=load(11))

    settings = get_settings()
    llm = LLMClient(settings.llm_credentials(), settings.limits)
    started = time.time()
    result = campaign.run(body, settings, llm, allow_network=False)
    duree = time.time() - started

    out = result.output
    print(f"statut            : {out.status.value}")
    print(f"document          : {out.document_status.value}")
    print(f"vérificateur      : {result.verifier_status} ({result.verifications} passe(s))")
    print(f"verdict           : {out.report.verdict.value}")
    print(f"justification     : {out.report.verdict_justification}")
    print(f"étapes examinées  : {len(out.etapes_presentes)} présentes, {len(out.etapes_absentes)} "
          f"absentes, {len(out.etapes_non_verifiees)} non vérifiées")
    print(f"constats          : {len(out.audit.constats)}")
    for constat in out.audit.constats:
        print(f"   - [{constat.code}] ({constat.severite.value}/{constat.axe.value}) "
              f"{constat.constat[:110]}")
        print(f"       preuve : {constat.preuve[:140]}")
    print(f"faits infirmés    : {[c.code for c in out.audit.constats_infirmes]}")
    print(f"non vérifiable    : {len(out.non_verifiable)} élément(s)")
    for item in out.non_verifiable[:3]:
        print(f"   - ({item.portee}) {item.element}")
    print(f"recommandations   : {len(out.report.recommandations)}")
    print(f"confiance         : {out.confidence.overall} — {out.confidence.rationale}")
    print(f"appels LLM        : {result.llm_calls} | tentative(s) : {result.attempts} | "
          f"reformulations : {result.reformulations}")
    print(f"durée             : {duree:.1f} s")

    (CHAINE / "stage13.json").write_text(json.dumps(
        {"output": out.model_dump(mode="json"),
         "verifier_status": result.verifier_status,
         "verifier": result.verifier.model_dump(mode="json") if result.verifier else None},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print("sortie :", CHAINE / "stage13.json")
    return 0 if result.verifier_status == "verified" else 9


if __name__ == "__main__":
    raise SystemExit(main())
