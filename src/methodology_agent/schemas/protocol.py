"""Protocole de recherche (étage P2) : le cœur du contrat d'analyse de l'agent 9.

Règle centrale (SPEC §10.3, §2) : ce contrat décrit un PROTOCOLE PRÉVU. Il n'offre aucun champ
permettant de présenter une collecte, une enquête ou une analyse comme DÉJÀ RÉALISÉE sans preuve.
"""

from enum import Enum

from pydantic import Field, field_validator, model_validator

from .common import LenientModel, StrictModel, StrList


class EchantillonnageType(str, Enum):
    probabiliste = "probabiliste"
    non_probabiliste = "non_probabiliste"
    exhaustif = "exhaustif"
    sans_objet = "sans_objet"


class SourceTaille(str, Enum):
    fournie = "fournie"          # l'étudiant a fourni un chiffre (exigence d'établissement, contrainte)
    documentee = "documentee"    # calcul ou règle de détermination explicite et justifié
    a_determiner = "a_determiner"  # aucune base : le champ reste vide et le manque est déclaré


class StatutAffirmation(str, Enum):
    prevu = "prevu"
    realise = "realise"          # exige une PREUVE fournie par l'étudiant
    a_confirmer = "a_confirmer"


class Population(StrictModel):
    cible: str = ""
    accessible: str = ""
    unite_analyse: str = ""


class Echantillonnage(StrictModel):
    type: EchantillonnageType = EchantillonnageType.non_probabiliste
    criteres_inclusion: StrList = Field(default_factory=list)
    criteres_exclusion: StrList = Field(default_factory=list)
    # Taille : soit un nombre, soit un texte (« 30 à 40 », « saturation »). Un nombre SANS
    # justification ni source est refusé par le contrôle déterministe P3.
    taille: int | None = None
    taille_texte: str = ""
    justification: str = ""
    source_taille: SourceTaille = SourceTaille.a_determiner
    # Quand l'échantillonnage est « sans_objet » (recherche documentaire, étude de cas unique…),
    # expliquer POURQUOI aucune population de personnes n'est échantillonnée.
    sans_objet_raison: str = ""

    @field_validator("taille")
    @classmethod
    def _positive(cls, v):
        if v is None:
            return v
        return int(v) if int(v) > 0 else None


class Donnee(LenientModel):
    categorie: str = ""
    description: str = ""
    # primaire (collectée), secondaire (bases existantes), documentaire (documents), mixte
    origine: str = ""


class TechniqueCollecte(LenientModel):
    nom: str = ""
    # Lien explicite avec les objectifs de recherche : c'est ce que le vérificateur (C5) exige.
    role: str = ""
    statut: StatutAffirmation = StatutAffirmation.prevu


class VariableIndicatrice(LenientModel):
    nom: str = ""
    # variable | indicateur | theme | categorie
    nature: str = ""
    modalites: StrList = Field(default_factory=list)


class Instrument(LenientModel):
    # questionnaire | guide_entretien | grille_observation | grille_documentaire | fiche_releve |
    # dictionnaire_variables | matrice
    type: str = ""
    objet: str = ""
    structure: StrList = Field(default_factory=list)
    # Un instrument est PROPOSÉ : il n'est jamais présenté comme administré ou testé.
    statut: str = "propose"

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, data):
        """Le modèle nomme librement les champs d'un instrument (« nom », « description »,
        « rubriques »…) : on accepte ses variantes au lieu de perdre la campagne entière pour un
        synonyme (constaté en exécution réelle : 6 erreurs de validation au premier essai)."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        mapping = {
            "type": ("type", "nom", "instrument", "nom_instrument", "titre"),
            "objet": ("objet", "objectif", "description", "role", "but", "finalite", "à quoi il sert"),
            "structure": ("structure", "rubriques", "sections", "items", "parties", "contenu"),
            "statut": ("statut", "status", "etat"),
        }
        for target, keys in mapping.items():
            if str(out.get(target, "") or "").strip() or (target == "structure"
                                                          and out.get("structure")):
                continue
            for key in keys:
                if key in out and str(out.get(key, "") or "").strip():
                    out[target] = out[key]
                    break
        return out


class MethodeAnalyse(LenientModel):
    nom: str = ""
    objet: str = ""
    # Conditions d'application (test statistique : distribution, taille, indépendance…).
    conditions: StrList = Field(default_factory=list)
    statut: StatutAffirmation = StatutAffirmation.prevu

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, data):
        """Le modèle écrit parfois « methode » / « description » au lieu de « nom » / « objet »."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if not str(out.get("nom", "") or "").strip():
            for key in ("methode", "nom", "method", "titre", "type"):
                if key in out and str(out.get(key, "") or "").strip():
                    out["nom"] = out[key]
                    break
        if not str(out.get("objet", "") or "").strip():
            for key in ("objet", "description", "but", "role"):
                if key in out and str(out.get(key, "") or "").strip():
                    out["objet"] = out[key]
                    break
        if not out.get("conditions"):
            for key in ("conditions", "conditions_application", "conditions_d_application"):
                if out.get(key):
                    out["conditions"] = out[key]
                    break
        return out


class Qualite(StrictModel):
    criteres: StrList = Field(default_factory=list)
    mesures: StrList = Field(default_factory=list)


class Ethique(StrictModel):
    concerne_personnes: bool = False
    mesures: StrList = Field(default_factory=list)
    autorisations_necessaires: StrList = Field(default_factory=list)
    # Ne jamais affirmer qu'une autorisation a été obtenue sans preuve (SPEC §7.G, §10.4).
    autorisations_obtenues: str = ""
    autorisations_preuve: str = ""


class Limite(LenientModel):
    description: str = ""
    consequence: str = ""


class EtapeMiseEnOeuvre(LenientModel):
    ordre: int = 0
    intitule: str = ""
    a_confirmer: bool = False


class Protocol(StrictModel):
    # --- les six choix REPRIS du diagnostic de l'agent 8 (jamais re-tranchés ici) ---
    approche: str = ""
    logique: str = ""
    type_recherche: str = ""
    strategie: str = ""
    # --- le protocole opérationnel ---
    terrain: str = ""
    population: Population = Field(default_factory=Population)
    echantillonnage: Echantillonnage = Field(default_factory=Echantillonnage)
    donnees: list[Donnee] = Field(default_factory=list)
    techniques: list[TechniqueCollecte] = Field(default_factory=list)
    variables_indicateurs: list[VariableIndicatrice] = Field(default_factory=list)
    analyses: list[MethodeAnalyse] = Field(default_factory=list)
    instruments: list[Instrument] = Field(default_factory=list)
    qualite: Qualite = Field(default_factory=Qualite)
    ethique: Ethique = Field(default_factory=Ethique)
    limites: list[Limite] = Field(default_factory=list)
    etapes: list[EtapeMiseEnOeuvre] = Field(default_factory=list)
    # Contradictions constatées avec le diagnostic vérifié (déclarées, jamais corrigées en silence).
    contradictions_diagnostic: StrList = Field(default_factory=list)
