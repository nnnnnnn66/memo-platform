"""Synthèse scientifique : réponse à la question, bilan des objectifs et des hypothèses (SPEC §9 étapes 1-2)."""

from enum import Enum

from pydantic import Field

from .common import LenientModel, StrictModel, StrList


class StatutObjectif(str, Enum):
    atteint = "atteint"
    partiellement_atteint = "partiellement_atteint"
    non_atteint = "non_atteint"
    non_evalue = "non_evalue"


class StatutHypothese(str, Enum):
    soutenue = "soutenue"
    non_soutenue = "non_soutenue"
    non_examinable = "non_examinable"


class BilanObjectif(LenientModel):
    objectif: str = ""
    statut: StatutObjectif = StatutObjectif.non_evalue
    #: Identifiants des résultats de l'étape 10 qui étayent ce bilan (traceabilité).
    resultats: StrList = Field(default_factory=list)
    commentaire: str = ""


class BilanHypothese(LenientModel):
    hypothese: str = ""
    statut: StatutHypothese = StatutHypothese.non_examinable
    justification: str = ""
    resultats: StrList = Field(default_factory=list)


class ReponseQuestion(LenientModel):
    question: str = ""
    reponse: str = ""
    etayage: StrList = Field(default_factory=list)      # identifiants de résultats
    portee: str = ""                                     # ce que la réponse permet, et ne permet pas


class Synthesis(StrictModel):
    elements_disponibles: StrList = Field(default_factory=list)
    elements_manquants: StrList = Field(default_factory=list)
    incoherences: StrList = Field(default_factory=list)
    resultats_essentiels: StrList = Field(default_factory=list)   # identifiants R…
    reponse_question: ReponseQuestion = Field(default_factory=ReponseQuestion)
    bilan_objectifs: list[BilanObjectif] = Field(default_factory=list)
    bilan_hypotheses: list[BilanHypothese] = Field(default_factory=list)
    plan_seulement: bool = False
    provenance: str = "provided"
