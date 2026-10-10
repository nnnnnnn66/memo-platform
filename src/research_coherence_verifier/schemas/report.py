"""Rapport d'audit : ce qui est remis à l'étudiant et à son directeur de mémoire (SPEC §9 étape 4)."""

from enum import Enum

from pydantic import Field

from .audit import ElementNonVerifiable, Finding, Severite
from .common import LenientModel, StrictModel, StrList


class Verdict(str, Enum):
    """Verdict GLOBAL — hiérarchie imposée, calculée par le programme (pas par le modèle)."""

    coherent = "coherent"
    coherent_avec_reserves = "coherent_avec_reserves"
    incoherent = "incoherent"


class Recommandation(LenientModel):
    code: str = ""
    action: str = ""
    vers_etape: str = ""            # étape du parcours à reprendre, si elle est identifiable


class CoherenceReport(StrictModel):
    synthese: str = ""
    constats: list[Finding] = Field(default_factory=list)
    recommandations: list[Recommandation] = Field(default_factory=list)
    non_verifiable: list[ElementNonVerifiable] = Field(default_factory=list)
    verdict: Verdict = Verdict.coherent
    verdict_justification: str = ""


def verdict_from(constats: list[Finding]) -> Verdict:
    """Grille imposée : un bloqueur ⇒ incohérent ; un majeur ⇒ cohérent avec réserves."""
    if any(f.severite == Severite.bloqueur for f in constats):
        return Verdict.incoherent
    if any(f.severite == Severite.majeur for f in constats):
        return Verdict.coherent_avec_reserves
    return Verdict.coherent


def verdict_justification(constats: list[Finding], verdict: Verdict) -> str:
    compte = {niveau: sum(1 for f in constats if f.severite == niveau)
              for niveau in (Severite.bloqueur, Severite.majeur, Severite.mineur)}
    texte = (f"{compte[Severite.bloqueur]} constat(s) bloquant(s), "
             f"{compte[Severite.majeur]} majeur(s), {compte[Severite.mineur]} mineur(s)")
    return f"verdict « {verdict.value} » : {texte}"


__all__ = ["CoherenceReport", "Recommandation", "Verdict", "verdict_from", "verdict_justification",
           "StrList"]
