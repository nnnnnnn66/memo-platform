"""Analyse préalable (étage P1) : ce que l'agent comprend du dossier avant de bâtir le protocole.

Distinct du diagnostic de l'agent 8 : ici on ne re-tranche AUCUN choix méthodologique, on établit
ce qui est disponible, ce qui manque (bloquant) et ce qui se contredit dans le socle reçu.
"""

from pydantic import Field

from .common import StrictModel, StrList


class Analysis(StrictModel):
    discipline: str = ""
    # Ce sur quoi le protocole peut s'appuyer (diagnostic vérifié, question, objectifs, hypothèses,
    # consignes académiques, accès au terrain, données disponibles…).
    elements_disponibles: StrList = Field(default_factory=list)
    # Manques BLOQUANTS uniquement : sans eux, aucun protocole défendable ne peut être produit.
    # Les incertitudes non bloquantes vont dans `unknowns` (même séparation que l'agent 8, règle R3).
    elements_manquants: StrList = Field(default_factory=list)
    # Contradictions entre le diagnostic de l'agent 8 et les éléments du dossier (jamais corrigées
    # en silence : elles sont signalées et le document est marqué « à réviser »).
    contradictions: StrList = Field(default_factory=list)
    # Incertitudes NON bloquantes, déclarées par le modèle.
    unknowns: StrList = Field(default_factory=list)
    provenance: str = "provided"
