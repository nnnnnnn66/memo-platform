"""Configuration du site web."""

import dataclasses
import os
import pathlib

import yaml
from dotenv import load_dotenv

RACINE = pathlib.Path(__file__).resolve().parents[3]
FICHIER = RACINE / "config" / "settings-site.yaml"


def _charger_secrets() -> None:
    """Secrets : fichier du PROJET (.env) puis fichier HERMES (~/.hermes/.env).

    Même règle que les agents : `load_dotenv` n'écrase rien, le projet garde la priorité. Sans ce
    chargement, un réglage posé dans `~/.hermes/.env` (emplacement documenté) resterait invisible
    au site — c'est ce qui est arrivé à la clé d'un agent.
    """
    load_dotenv(RACINE / ".env")
    hermes_home = pathlib.Path(os.environ.get("HERMES_HOME", pathlib.Path.home() / ".hermes"))
    load_dotenv(hermes_home / ".env")


@dataclasses.dataclass(frozen=True)
class Settings:
    orchestrateur_url: str
    duree_session_heures: int
    max_tentatives: int
    blocage_minutes: int
    invitations_requises: bool
    base_comptes: pathlib.Path
    dossier_templates: pathlib.Path
    dossier_static: pathlib.Path


def charger(chemin: pathlib.Path | None = None) -> Settings:
    _charger_secrets()
    fichier = chemin or FICHIER
    brut = {}
    if fichier.exists():
        brut = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}
    site = brut.get("site") or {}
    securite = brut.get("securite") or {}
    chemins = brut.get("paths") or {}
    return Settings(
        orchestrateur_url=str(site.get("orchestrateur_url", "http://127.0.0.1:8000")).rstrip("/"),
        duree_session_heures=int(securite.get("duree_session_heures", 12)),
        max_tentatives=int(securite.get("max_tentatives", 5)),
        blocage_minutes=int(securite.get("blocage_minutes", 15)),
        invitations_requises=bool(site.get("invitations_requises", True)),
        base_comptes=RACINE / str(chemins.get("base_comptes", "workspace/site.db")),
        dossier_templates=RACINE / str(chemins.get("templates", "templates")),
        dossier_static=RACINE / "src" / "site_web" / "static",
    )
