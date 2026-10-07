"""Registre des fournisseurs documentaires (chargé depuis providers.yaml).

La liste vit en configuration : ajouter un fournisseur gratuit utile = éditer le fichier.
L'hôte de chaque fournisseur est la seule destination API autorisée (anti-SSRF).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

KIND_TO_FAMILIES = {
    "publications": ("publications",),
    "theses": ("theses",),
    "repositories": ("repositories",),
    "statistics": ("statistics",),
    "any": ("publications", "theses", "repositories"),
}

# Ordre de préférence par famille (qualité des métadonnées et accès au texte intégral).
FAMILY_ORDER = {
    "publications": ["openalex", "crossref", "europepmc", "doaj", "pubmed"],
    "theses": ["theses_fr", "hal", "openaire", "datacite"],
    "repositories": ["hal", "zenodo", "openaire", "arxiv", "osf", "datacite"],
    "statistics": ["datagouv", "dataeuropa"],
}


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    family: str
    source_type: str
    host: str
    adapter: str
    pdf: bool = False
    enabled: bool = True
    note: str = ""


@dataclass(frozen=True)
class Enrichment:
    id: str
    label: str
    host: str
    adapter: str
    enabled: bool = True


class Registry:
    def __init__(self, providers_file: Path) -> None:
        raw = yaml.safe_load(Path(providers_file).read_text(encoding="utf-8"))
        self.providers = [
            Provider(
                id=p["id"], label=p.get("label", p["id"]), family=p["family"],
                source_type=p["source_type"], host=p["host"], adapter=p["adapter"],
                pdf=bool(p.get("pdf", False)), enabled=bool(p.get("enabled", True)),
                note=p.get("note", ""),
            )
            for p in raw.get("providers", [])
        ]
        self.enrichments = [
            Enrichment(id=e["id"], label=e.get("label", e["id"]), host=e["host"],
                       adapter=e["adapter"], enabled=bool(e.get("enabled", True)))
            for e in raw.get("enrichment", [])
        ]

    # --- contexte sécurité ---
    def allowed_hosts(self) -> set[str]:
        """Hôtes autorisés pour les API : fournisseurs et services d'enrichissement ACTIFS."""
        hosts = {p.host for p in self.providers if p.enabled}
        hosts |= {e.host for e in self.enrichments if e.enabled}
        return hosts

    def by_id(self, provider_id: str) -> Provider | None:
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        return None

    def enrichment(self, enrichment_id: str) -> Enrichment | None:
        for item in self.enrichments:
            if item.id == enrichment_id:
                return item
        return None

    # --- sélection déterministe ---
    def select(self, kind: str) -> list[Provider]:
        families = KIND_TO_FAMILIES.get(kind, KIND_TO_FAMILIES["any"])
        ordered: list[Provider] = []
        for family in families:
            for provider_id in FAMILY_ORDER.get(family, []):
                provider = self.by_id(provider_id)
                if provider and provider.enabled and provider.family == family:
                    ordered.append(provider)
        for provider in self.providers:
            if provider.enabled and provider.family in families and provider not in ordered:
                ordered.append(provider)
        return ordered

    def adapter_module(self, provider):
        """Import de l'adaptateur (nom contrôlé par la configuration, jamais par une donnée).

        Accepte un `Provider` ou un `Enrichment` : les deux exposent `.adapter`.
        """
        from importlib import import_module

        known = {p.adapter for p in self.providers} | {e.adapter for e in self.enrichments}
        if provider.adapter not in known:
            raise ValueError(f"adaptateur inconnu : {provider.adapter}")
        return import_module(f"{__package__}.adapters.{provider.adapter}")
