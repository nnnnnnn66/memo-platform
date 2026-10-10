"""Constats d'audit (SPEC §9) — un constat sans PREUVE est refusé par le programme."""

from enum import Enum

from pydantic import Field

from .common import LenientModel, StrictModel, StrList


class Severite(str, Enum):
    bloqueur = "bloqueur"
    majeur = "majeur"
    mineur = "mineur"


class Axe(str, Enum):
    completude = "completude"
    decoulement = "decoulement"
    service = "service"
    examinabilite = "examinabilite"
    couverture = "couverture"
    fidelite = "fidelite"
    tracabilite = "tracabilite"
    fusion = "fusion"
    contradiction = "contradiction"
    integrite = "integrite"


class Origine(str, Enum):
    deterministe = "deterministe"   # établi par le programme (X1–X12)
    llm = "llm"                     # relevé par l'audit sémantique


class Suite(str, Enum):
    confirme = "confirme"
    nuance = "nuance"
    infirme = "infirme"


class Finding(LenientModel):
    """Un constat de rupture, de fragilité ou d'incohérence."""

    code: str = ""                  # X1–X12 (fait) ou LIBRE (constat sémantique)
    axe: Axe = Axe.integrite
    severite: Severite = Severite.mineur
    elements: StrList = Field(default_factory=list)   # quelles étapes/pièces sont concernées
    constat: str = ""               # ce qui est constaté, en une phrase
    preuve: str = ""                # OÙ c'est constaté (OBLIGATOIRE)
    recommandation: str = ""        # ce qui est recommandé
    origine: Origine = Origine.deterministe
    suite: Suite = Suite.confirme    # ce que l'audit sémantique a fait de ce constat
    motif_suite: str = ""            # pourquoi il l'a confirmé, nuancé ou infirmé


class ElementNonVerifiable(LenientModel):
    """Ce que l'audit n'a PAS pu vérifier (SPEC §7.3) — toujours déclaré."""

    element: str = ""
    raison: str = ""
    portee: str = "statique"        # statique (par nature) | dynamique (manque dans le dossier)


class DossierState(StrictModel):
    """État de complétude du dossier (aucun modèle sollicité)."""

    etapes_presentes: StrList = Field(default_factory=list)
    etapes_verifiees: StrList = Field(default_factory=list)
    etapes_non_verifiees: StrList = Field(default_factory=list)
    etapes_absentes: StrList = Field(default_factory=list)
    elements_de_service: StrList = Field(default_factory=list)   # sujet, question, objectifs…
    elements_de_service_absents: StrList = Field(default_factory=list)
    exploitable: bool = False


class AuditItem(StrictModel):
    """Un constat HORS de la liste déterministe, relevé par l'audit sémantique."""

    code: str = ""                  # facultatif (X… si le constat prolonge un fait, sinon LIBRE)
    axe: Axe
    severite: Severite = Severite.mineur
    elements: StrList = Field(default_factory=list)
    constat: str = ""
    preuve: str = ""
    recommandation: str = ""


class Audit(StrictModel):
    """Audit transversal consolidé : faits déterministes + apports du modèle."""

    dossier: DossierState = Field(default_factory=DossierState)
    constats: list[Finding] = Field(default_factory=list)
    #: Faits déterministes infirmés par l'examen sémantique, avec le motif (jamais supprimés en silence).
    constats_infirmes: list[Finding] = Field(default_factory=list)
