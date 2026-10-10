"""Rejoue UNIQUEMENT le vérificateur de l'Agent 3 sur une sortie déjà produite.

Évite de refaire les 25 minutes de collecte/téléchargement/analyse : la sortie est relue depuis
`workspace/chaine-live/stage3.json`, et seuls les appels au vérificateur sont rejoués.

Usage :
    set -a; . ~/.hermes/.env; set +a
    PYTHONPATH=src .venv/bin/python scripts/replay_verif_litterature.py
"""

import json
import pathlib
import sys
from types import SimpleNamespace

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

from literature_review_agent.core.config import get_settings  # noqa: E402
from literature_review_agent.llm.client import LLMClient  # noqa: E402
from literature_review_agent.pipeline import verifier  # noqa: E402
from literature_review_agent.schemas.input import CampaignRequest  # noqa: E402
from literature_review_agent.schemas.output import ReviewOutput  # noqa: E402

payload = json.loads((ROOT / "workspace" / "chaine-live" / "stage3.json").read_text())["output"]
output = ReviewOutput.model_validate(payload)

request = CampaignRequest(
    student_id="chaine-etu", session_id="chaine-live",
    subject_text="Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024",
    research_problem="Les entreprises de services numériques d'Abidjan constatent, depuis le passage "
                     "au télétravail en 2020, une dégradation de la tenue des délais et une "
                     "coordination affaiblie entre développeurs.",
    discipline="Sciences de gestion", academic_level="Master 2", country="Côte d'Ivoire",
    geographical_scope="Abidjan", period="2020-2024")

settings = get_settings()
llm = LLMClient(settings.llm_credentials(), settings.limits)

# Bibliographie RE-RENDUE avec le code courant : c'est ce que produirait une nouvelle campagne, et
# cela permet de juger le correctif de normalisation des noms sans refaire 25 minutes de collecte.
from literature_review_agent.bibliography import styles  # noqa: E402

_style = request.citation_style or "apa7"
if hasattr(_style, "value"):
    _style = _style.value
_avant = list(output.bibliography.entries)
_entries = [styles.render(doc, _style) for doc in output.corpus.documents]
output.bibliography.entries = _entries
output.bibliography.entries_count = len(_entries)
# Chaque document porte AUSSI sa propre référence (rendue pendant la campagne) : sans la re-rendre,
# le vérificateur continue de lire l'ancienne forme mal découpée et le rejeu serait injuste.
for _doc in output.corpus.documents:
    _doc.reference = styles.render(_doc, _style)
print(f"bibliographie re-rendue : {len(_entries)} entrées, "
      f"{sum(1 for a, b in zip(_avant, _entries) if a != b)} modifiée(s) par le correctif", flush=True)

# Le vérificateur reçoit normalement les enregistrements INTERNES du corpus (CorpusRecord), que le
# pipeline ne persiste pas. On les reconstruit depuis les documents de la sortie (champs communs) —
# seule `is_oa` manque (posée à False) et `term_hits` n'est pas utilisé par le bloc corpus.
import dataclasses  # noqa: E402

from literature_review_agent.sources.corpus import CorpusRecord  # noqa: E402

_champs = {f.name for f in dataclasses.fields(CorpusRecord)}
records = []
for doc in output.corpus.documents:
    data = doc.model_dump()
    data["is_oa"] = bool(data.get("is_oa", False))
    records.append(CorpusRecord(**{k: v for k, v in data.items() if k in _champs}))
print(f"corpus transmis : {len(records)} documents (dont {records[0].doc_id} … {records[-1].doc_id})",
      flush=True)

# On transmet la LISTE des documents réellement retenus — exactement ce que fait la campagne
# corrigée (le collecteur complet était tronqué à ses 60 premiers documents collectés).
verdict = verifier.verify(llm, request, output, records)

print("=" * 78)
print("VERDICT          :", verdict.verdict.value)
print("APPELS LLM       :", llm.calls)
print("CONTRÔLES        :")
for c in verdict.controls:
    print(f"   {c.code} = {c.resultat} — {(c.detail or '')[:150]}")
print("CORRECTIONS      :")
for c in verdict.corrections:
    print("   -", c)
print("SIGNALEMENTS     :")
for f in verdict.flags:
    print("   -", f)
print("=" * 78)
