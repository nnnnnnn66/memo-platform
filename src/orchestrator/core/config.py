"""Configuration de l'orchestrateur — carte des étapes lue depuis un fichier, jamais codée en dur.

Ajouter ou déplacer une étape = **configuration**, pas code : la carte du parcours et le pont
entre étapes vivent dans `config/settings-orchestrateur.yaml`.
"""

import pathlib
from dataclasses import dataclass, field

import yaml

RACINE = pathlib.Path(__file__).resolve().parents[3]
FICHIER_CONFIG = RACINE / "config" / "settings-orchestrateur.yaml"


@dataclass(frozen=True)
class Etape:
    """Une étape du parcours et l'agent qui la sert."""

    numero: int
    agent: str
    libelle: str
    port: int
    prefixe: str
    route_analyse: str
    upstream: dict = field(default_factory=dict)
    finale: bool = False
    # Champs de base que CET agent accepte réellement. Vide = la liste globale `base` s'applique.
    # Chaque agent a SON contrat (`extra="forbid"`) : envoyer un champ qu'il ne déclare pas fait
    # échouer l'étape avec un 422 « Extra inputs are not permitted ».
    champs: tuple = ()
    # Une phrase, écrite POUR L'ÉTUDIANT, qui dit ce que l'étape lui demandera. Sans elle, une
    # étape à venir n'est qu'une ligne grise : l'étudiant ne sait pas ce qui l'attend, donc il
    # subit le parcours au lieu de l'anticiper.
    resume: str = ""

    def url_analyse(self, hote: str) -> str:
        return f"http://{hote}:{self.port}{self.route_analyse}"

    def url_lecture(self, hote: str, etudiant: str, session: str) -> str:
        return f"http://{hote}:{self.port}{self.prefixe}/{etudiant}/{session}"

    def url_decision(self, hote: str, etudiant: str, session: str) -> str:
        return f"http://{hote}:{self.port}{self.prefixe}/{etudiant}/{session}/decision"


@dataclass(frozen=True)
class Settings:
    mode: str
    hote: str
    timeout: int
    analyses_par_jour: int
    etapes: tuple
    workspace_dir: pathlib.Path
    state_db: pathlib.Path
    champs_base: tuple = ("student_id", "session_id", "subject_text")

    @property
    def par_numero(self) -> dict:
        return {etape.numero: etape for etape in self.etapes}

    @property
    def premiere(self) -> Etape:
        return self.etapes[0]

    def suivante(self, numero: int):
        """Étape suivante du parcours, ou None si c'était la dernière."""
        ordre = [etape.numero for etape in self.etapes]
        if numero not in ordre:
            return None
        index = ordre.index(numero)
        return self.etapes[index + 1] if index + 1 < len(self.etapes) else None


def charger(chemin: pathlib.Path | None = None) -> Settings:
    """Charge la configuration et VALIDE la carte : une étape qui attend une sortie d'une étape
    inexistante est refusée au démarrage, pas au milieu d'un dossier d'étudiant."""
    fichier = chemin or FICHIER_CONFIG
    brut = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}

    transport = brut.get("transport") or {}
    quota = brut.get("quota") or {}
    etapes = tuple(
        Etape(
            numero=int(item["numero"]),
            agent=str(item["agent"]),
            libelle=str(item.get("libelle", "")),
            port=int(item["port"]),
            prefixe=str(item["prefixe"]).rstrip("/"),
            route_analyse=str(item["route_analyse"]),
            upstream={str(champ): int(source) for champ, source in (item.get("upstream") or {}).items()},
            finale=bool(item.get("finale", False)),
            champs=tuple(str(champ) for champ in (item.get("champs") or ())),
            # Le chargeur construit l'étape CHAMP PAR CHAMP : ajouter un champ au dataclass ET au
            # YAML ne suffit pas — il faut aussi le lire ici, sinon il reste vide en silence.
            resume=str(item.get("resume", "")),
        )
        for item in (brut.get("etapes") or [])
    )
    if not etapes:
        raise ValueError("Aucune étape déclarée dans settings-orchestrateur.yaml")

    numeros = {etape.numero for etape in etapes}
    # L'ORDRE DU PARCOURS EST L'ORDRE DE DÉCLARATION, pas l'ordre des numéros. Le numéro reste un
    # identifiant interne stable (il saute le 12, réservé) : imposer un ordre numérique
    # interdirait de placer la vérification globale avant la conclusion, comme le veut le porteur.
    positions = {etape.numero: rang for rang, etape in enumerate(etapes)}
    for etape in etapes:
        for champ, source in etape.upstream.items():
            if source not in numeros:
                raise ValueError(
                    f"Étape {etape.numero} : « {champ} » attend la sortie de l'étape {source}, "
                    "qui n'existe pas")
            if positions[source] >= positions[etape.numero]:
                raise ValueError(
                    f"Étape {etape.numero} : « {champ} » ne peut venir que d'une étape "
                    f"ANTÉRIEURE dans le parcours (l'étape {source} vient après elle)")

    paths = brut.get("paths") or {}
    return Settings(
        mode=str(transport.get("mode", "http")).lower(),
        hote=str(transport.get("hote", "127.0.0.1")),
        timeout=int(transport.get("timeout", 1800)),
        analyses_par_jour=int(quota.get("analyses_par_jour", 20)),
        etapes=etapes,
        workspace_dir=RACINE / str(paths.get("workspace", "workspace")),
        state_db=RACINE / str(paths.get("state_db", "workspace/orchestrateur.db")),
        champs_base=tuple(str(champ) for champ in (brut.get("base")
                                                   or ["student_id", "session_id", "subject_text"])),
    )
