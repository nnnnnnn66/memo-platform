"""Registre des fournisseurs de sources : chargé depuis providers.yaml.

La liste vit en CONFIGURATION (cadre propre à l'agent) : ajouter un fournisseur gratuit
utile à l'objectif ne demande aucune modification du pipeline. L'hôte de chaque fournisseur
est la SEULE destination réseau autorisée (anti-SSRF).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

# Familles consultées selon le type de recherche demandé par l'agent.
KIND_TO_FAMILIES = {
    "publications": ("publications",),
    "repository": ("repositories",),
    "statistics": ("statistics",),
    "any": ("publications", "repositories", "statistics"),
}

# Ordre de préférence par famille (pertinence/qualité des métadonnées), SPEC §7.
FAMILY_ORDER = {
    "publications": ["openalex", "crossref", "europepmc", "doaj", "pubmed", "openaire"],
    "repositories": ["hal", "openaire", "zenodo", "datacite", "arxiv"],
    "statistics": ["datagouv", "dataeuropa", "datacite", "zenodo"],
}


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    family: str
    source_type: str
    host: str
    adapter: str
    enabled: bool = True
    note: str = ""


class Registry:
    def __init__(self, providers_file: Path) -> None:
        raw = yaml.safe_load(Path(providers_file).read_text(encoding="utf-8"))
        self.providers = [
            Provider(
                id=p["id"], label=p.get("label", p["id"]), family=p["family"],
                source_type=p["source_type"], host=p["host"], adapter=p["adapter"],
                enabled=bool(p.get("enabled", True)), note=p.get("note", ""),
            )
            for p in raw.get("providers", [])
        ]

    # --- contexte sécurité ---
    def allowed_hosts(self) -> set[str]:
        """Hôtes autorisés : ceux des fournisseurs ACTIFS uniquement."""
        return {p.host for p in self.providers if p.enabled}

    def by_id(self, provider_id: str) -> Provider | None:
        for p in self.providers:
            if p.id == provider_id:
                return p
        return None

    # --- sélection déterministe ---
    def select(self, kind: str) -> list[Provider]:
        """Fournisseurs pertinents pour un type de recherche, dans l'ordre de préférence."""
        families = KIND_TO_FAMILIES.get(kind, KIND_TO_FAMILIES["any"])
        ordered: list[Provider] = []
        for family in families:
            for provider_id in FAMILY_ORDER.get(family, []):
                provider = self.by_id(provider_id)
                if provider and provider.enabled and provider.family == family:
                    ordered.append(provider)
        # Fournisseurs activés mais absents de l'ordre explicite : ajoutés en fin de liste.
        for provider in self.providers:
            if provider.enabled and provider.family in families and provider not in ordered:
                ordered.append(provider)
        return ordered

    def adapter_module(self, provider: Provider):
        """Import du module d'adaptation (aucun code dynamique issu de données)."""
        from importlib import import_module

        if provider.adapter not in {p.adapter for p in self.providers}:
            raise ValueError(f"adaptateur inconnu : {provider.adapter}")
        return import_module(f"{__package__}.adapters.{provider.adapter}")
