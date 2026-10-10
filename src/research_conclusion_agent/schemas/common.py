"""Modèles partagés entre les contrats de l'Agent Méthodologie (étape 9)."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, BeforeValidator, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LenientModel(BaseModel):
    """Modèle TOLÉRANT aux champs inconnus.

    Réservé aux objets DESCRIPTIFS produits librement par le modèle (instrument, méthode d'analyse,
    technique, limite…) : le modèle nomme ces sous-objets comme il l'entend, et un synonyme ne doit
    pas faire échouer une campagne entière pour six « extra inputs are not permitted » (constaté en
    exécution réelle). Les CONTRATS (entrée, sortie, étage) restent stricts.
    """

    model_config = ConfigDict(extra="ignore")


class Confidence(StrictModel):
    overall: float = 0.0
    rationale: str = ""

    @field_validator("overall")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class Validation(StrictModel):
    """Résultat de la vérification indépendante. Posé par le vérificateur, jamais par l'agent."""

    verified: bool = False
    verifier_status: str = "pending"


class UpstreamValidation(BaseModel):
    model_config = ConfigDict(extra="allow")
    verified: bool = False
    verifier_status: str = "pending"


def flatten_strings(items) -> list[str]:
    """Ramène une entrée hétérogène à une liste de CHAÎNES.

    Le modèle renvoie régulièrement des OBJETS là où le contrat attend des chaînes (constaté en
    exécution réelle : 17 erreurs de validation, deux tentatives de suite, campagne morte). On
    aplatit l'objet en texte au lieu de refuser : l'information est CONSERVÉE, jamais inventée.
    Même famille de correctif que les agents 3, 4, 7 et 8.

    ATTENTION : une CHAÎNE seule (au lieu d'une liste) est prise telle quelle — l'itérer la
    découperait caractère par caractère (« m », « o », « d »…), défaut constaté en campagne réelle
    et signalé par le vérificateur (« tableaux éclatés caractère par caractère, illisibles »).
    """
    if items is None:
        return []
    if isinstance(items, str):
        return [items.strip()] if items.strip() else []
    if isinstance(items, dict):
        items = [items]
    out: list[str] = []
    for item in items:
        if isinstance(item, dict):
            parts: list[str] = []
            for key, value in item.items():
                if isinstance(value, (list, tuple)):
                    value = ", ".join(str(v) for v in value)
                text = str(value).strip()
                if text:
                    parts.append(f"{key} : {text}" if len(item) > 1 else text)
            out.append(" — ".join(parts))
        elif item is not None:
            out.append(str(item))
    return [text for text in out if text.strip()]


#: Liste de chaînes TOLÉRANTE : accepte des objets et les aplatit en texte.
StrList = Annotated[list[str], BeforeValidator(flatten_strings)]
