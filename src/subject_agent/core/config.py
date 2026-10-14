"""Configuration : réglages (settings.yaml) + secrets (.env). Jamais de secret en clair en sortie."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .limits import Limits

# src/subject_agent/core/config.py -> parents[3] == racine du projet
ROOT = Path(__file__).resolve().parents[3]


def _load_secrets(root: Path) -> None:
    """Charge les secrets : fichier du PROJET (.env) puis fichier HERMES (~/.hermes/.env).

    `load_dotenv` n'écrase jamais une variable déjà définie : le projet garde la priorité, et le
    fichier Hermes comble ce qui manque. Sans ce second chargement, une clé posée dans
    `~/.hermes/.env` (emplacement documenté dans le README) n'était JAMAIS lue par les agents :
    la consigne ne fonctionnait pas en exécution normale.
    """
    load_dotenv(root / ".env")
    hermes_home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    load_dotenv(Path(hermes_home) / ".env")


class Settings:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else ROOT
        _load_secrets(self.root)
        cfg_path = self.root / "config" / "settings.yaml"
        self.raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        self.limits = Limits.from_dict(self.raw["limits"])
        self.llm = self.raw["llm"]
        self.paths = self.raw["paths"]
        self.security = self.raw.get("security", {})
        # Couche de recherche documentaire réelle : sa présence rend l'agent capable d'ALLER
        # CHERCHER l'information au lieu de la réclamer à l'étudiant.
        self.sources = self.raw.get("sources", {})
        self.research = self.raw.get("research", {})

    @property
    def providers_file(self) -> Path:
        """Fichier des fournisseurs — chemin relatif au paquet `sources/` de CET agent."""
        return Path(__file__).resolve().parents[1] / "sources" / str(
            self.sources.get("providers_file", "providers.yaml"))

    @property
    def cache_db(self) -> Path:
        chemin = (self.paths or {}).get("cache_db")
        return self.root / str(chemin) if chemin else self.root / "workspace" / "subject-cache.db"

    # --- chemins ---
    @property
    def workspace_dir(self) -> Path:
        return self.root / self.paths["workspace"]

    @property
    def audit_db(self) -> Path:
        return self.root / self.paths["audit_db"]

    # --- LLM ---
    def llm_credentials(self) -> dict:
        """Résout le provider actif et sa clé depuis l'environnement (jamais logguée)."""
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
