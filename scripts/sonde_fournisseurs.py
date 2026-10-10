"""Sonde RÉELLE des fournisseurs documentaires de l'Agent 3 — aucun LLM, aucun coût.

Vérifie que chaque connecteur déclaré dans `providers.yaml` répond vraiment et renvoie des
documents exploitables. À lancer après tout ajout de fournisseur :

    cd /root/memo-platform && set -a; . ~/.hermes/.env; set +a
    PYTHONPATH=src .venv/bin/python scripts/sonde_fournisseurs.py [requête]

Sortie : un fournisseur par ligne — nombre de résultats, et un exemple (titre, DOI, type, accès
ouvert). Un fournisseur à 0 est signalé comme échec ou absence RÉELLE, jamais maquillé.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from literature_review_agent.core.config import Settings  # noqa: E402
from literature_review_agent.sources.http import ApiFetcher  # noqa: E402
from literature_review_agent.sources.registry import Registry  # noqa: E402

DEFAUT = "teletravail productivite salarie"


def main() -> None:
    requete = " ".join(sys.argv[1:]) or DEFAUT
    settings = Settings()
    registry = Registry(ROOT / "src" / "literature_review_agent" / "sources" / "providers.yaml")
    fetcher = ApiFetcher(settings.sources, settings.limits, registry.allowed_hosts())
    cibles = ["openalex", "crossref", "semanticscholar", "core", "hal", "doaj", "unpaywall"]
    print(f"requête : « {requete} »\n")
    for provider_id in cibles:
        provider = registry.by_id(provider_id) or registry.enrichment(provider_id)
        if provider is None:
            print(f"  {provider_id:16s} -> non déclaré")
            continue
        etat = "" if getattr(provider, "enabled", True) else " (désactivé)"
        module = registry.adapter_module(provider)
        if module is None:
            print(f"  {provider_id:16s} -> adaptateur absent{etat}")
            continue
        if not hasattr(module, "search"):
            print(f"  {provider_id:16s} -> enrichissement (pas un moteur de recherche){etat}")
            continue
        try:
            results = module.search(fetcher, requete, 5)
        except Exception as erreur:  # noqa: BLE001
            print(f"  {provider_id:16s} -> ÉCHEC {type(erreur).__name__}: {str(erreur)[:80]}{etat}")
            continue
        print(f"  {provider_id:16s} -> {len(results)} résultat(s){etat}")
        if results:
            premier = results[0]
            print(f"      « {str(premier.get('title'))[:68]} »")
            print(f"      doi={str(premier.get('doi') or '(aucun)')[:38]} | "
                  f"type={premier.get('document_type')} | accès ouvert={premier.get('is_oa')} | "
                  f"pdf proposés={len(premier.get('pdf_candidates') or [])}")


main()
