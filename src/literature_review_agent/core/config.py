"""Configuration de l'Agent Revue de littérature : config/settings-litterature.yaml + secrets (.env).

Aucun secret n'est exposé ni journalisé. Fichier de configuration distinct de ceux des autres
agents (cadre propre à chaque agent).
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .limits import Limits

# src/literature_review_agent/core/config.py -> parents[3] == racine du projet
ROOT = Path(__file__).resolve().parents[3]
CONFIG_NAME = "settings-litterature.yaml"


def _load_secrets(root: Path) -> None:
    """Secrets : fichier du PROJET (.env) puis fichier HERMES (~/.hermes/.env).

    `load_dotenv` n'écrase rien : le projet garde la priorité, Hermes comble le reste. Sans ce
    second chargement, `OPENALEX_API_KEY` posée dans `~/.hermes/.env` (emplacement documenté)
    n'était jamais lue par l'agent.
    """
    load_dotenv(root / ".env")
    hermes_home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    load_dotenv(Path(hermes_home) / ".env")


class Settings:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else ROOT
        _load_secrets(self.root)
        cfg_path = self.root / "config" / CONFIG_NAME
        self.raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        self.limits = Limits.from_dict(self.raw["limits"])
        self.llm = self.raw["llm"]
        self.paths = self.raw["paths"]
        self.sources = self.raw.get("sources", {})
        self.fulltext = self.raw.get("fulltext", {})
        self.bibliography = self.raw.get("bibliography", {})
        self.diagnosis = self.raw.get("diagnosis", {})
        self.security = self.raw.get("security", {})

    # --- chemins ---
    @property
    def workspace_dir(self) -> Path:
        return self.root / self.paths["workspace"]

    @property
    def audit_db(self) -> Path:
        return self.root / self.paths["audit_db"]

    @property
    def cache_db(self) -> Path:
        return self.root / self.paths["cache_db"]

    @property
    def providers_file(self) -> Path:
        name = self.sources.get("providers_file", "providers.yaml")
        return Path(__file__).resolve().parents[1] / "sources" / name

    # --- LLM ---
    def llm_credentials(self) -> dict:
        """Résout le provider actif et sa clé depuis l'environnement (jamais journalisée)."""
        provider = self.llm["provider"]
        prov = self.llm[provider]
        key = os.environ.get(prov["api_key_env"], "")
        return {
            "provider": provider,
            "base_url": prov["base_url"],
            "model": prov["model"],
            "api_key": key,
            "temperature": float(self.llm.get("temperature", 0.2)),
            "api_key_env": prov["api_key_env"],
        }


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
