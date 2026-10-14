"""Registre des fournisseurs du gap check (chargé depuis providers.yaml).

La liste vit en configuration : ajouter un fournisseur gratuit = éditer le fichier.
L'hôte de chaque fournisseur est la seule destination API autorisée (anti-SSRF).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    family: str
    host: str
    adapter: str
    enabled: bool = True
    note: str = ""


class Registry:
    def __init__(self, providers_file: Path) -> None:
        raw = yaml.safe_load(Path(providers_file).read_text(encoding="utf-8"))
        self.providers = [
            Provider(
                id=p["id"], label=p.get("label", p["id"]), family=p.get("family", "publications"),
                host=p["host"], adapter=p["adapter"], enabled=bool(p.get("enabled", True)),
                note=p.get("note", ""),
            )
            for p in raw.get("providers", [])
        ]

    def allowed_hosts(self) -> set[str]:
        return {p.host for p in self.providers if p.enabled}

    def enabled(self) -> list[Provider]:
        return [p for p in self.providers if p.enabled]

    def by_id(self, provider_id: str) -> Provider | None:
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        return None

    def adapter_module(self, provider: Provider):
        """Import de l'adaptateur (nom contrôlé par la configuration, jamais par une donnée)."""
        from importlib import import_module

        known = {p.adapter for p in self.providers}
        if provider.adapter not in known:
            raise ValueError(f"adaptateur inconnu : {provider.adapter}")
        return import_module(f"{__package__}.adapters.{provider.adapter}")
