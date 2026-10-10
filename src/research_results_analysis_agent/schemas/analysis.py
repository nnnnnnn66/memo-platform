"""Résultats CALCULÉS (moteur déterministe) et analyse (étage P2).

`ComputedResults` est produit EXCLUSIVEMENT par `analysis/data_engine.py`. Le modèle ne peut ni le
modifier ni y ajouter un résultat : il ne fait que le LIRE et l'interpréter (principe « les chiffres
viennent du code »).
"""

from enum import Enum

from pydantic import Field

from .common import LenientModel, StrictModel, StrList


class ComputedResult(LenientModel):
    """Un résultat CALCULÉ. Aucun champ n'est rempli par le modèle."""

    id: str = ""                 # R1, R2… référencé partout ensuite
    libelle: str = ""
    valeur: str = ""             # valeur formatée (« 42 », « 3,4 », « 62 % »)
    unite: str = ""
    effectif: int = 0            # effectif de référence (dénominateur)
    methode: str = ""            # calcul appliqué (effectif, frequence, moyenne, croisement…)
    variable: str = ""
    groupe: str = ""


class ComputedResults(StrictModel):
    resultats: list[ComputedResult] = Field(default_factory=list)
    notes: StrList = Field(default_factory=list)

    def ids(self) -> set[str]:
        return {r.id for r in self.resultats}

    def valeurs(self) -> set[str]:
        return {str(r.valeur) for r in self.resultats if str(r.valeur).strip()}

    def by_id(self, identifiant: str) -> "ComputedResult | None":
        for resultat in self.resultats:
            if resultat.id == identifiant:
                return resultat
        return None


class StatutHypothese(str, Enum):
    soutenue = "soutenue"
    non_soutenue = "non_soutenue"
    non_examinable = "non_examinable"


class Resultat(LenientModel):
    """Un résultat AFFIRMÉ dans l'analyse : il doit renvoyer à un calcul réel."""

    id_resultat: str = ""        # référence OBLIGATOIRE à un ComputedResult
    observation: str = ""
    objectif: str = ""
    limites: StrList = Field(default_factory=list)


class ExamenHypothese(LenientModel):
    hypothese: str = ""
    statut: StatutHypothese = StatutHypothese.non_examinable
    justification: str = ""
    resultats: StrList = Field(default_factory=list)


class AnalysisPlan(StrictModel):
    objectifs_couverts: StrList = Field(default_factory=list)
    objectifs_non_couverts: StrList = Field(default_factory=list)
    ecarts_methodologie: StrList = Field(default_factory=list)
    resultats: list[Resultat] = Field(default_factory=list)
    hypotheses: list[ExamenHypothese] = Field(default_factory=list)
    analyses_realisees: StrList = Field(default_factory=list)
    analyses_non_realisees: StrList = Field(default_factory=list)
    plan_seulement: bool = False       # vrai si aucune donnée exploitable : plan, jamais de résultats


class AnalysisOutputPayload(StrictModel):
    """Ce que l'étage P2 produit, hors parties calculées."""
    plan: AnalysisPlan = Field(default_factory=AnalysisPlan)
