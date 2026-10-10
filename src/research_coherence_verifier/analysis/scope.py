"""Portée de l'audit : ce que l'agent NE PEUT PAS vérifier (SPEC §7.3, exigence du porteur).

Deux natures :
- **statique** : ce qui échappe par nature à un audit conduit sur un dossier (véracité du terrain,
  plagiat, style, jugement du jury…) ;
- **dynamique** : ce que l'absence d'une étape rend inexplorable DANS CE dossier précis.
"""

from ..schemas.audit import ElementNonVerifiable

PORTEE_STATIQUE: tuple[ElementNonVerifiable, ...] = (
    ElementNonVerifiable(
        element="véracité des données recueillies",
        raison="Le dossier ne contient pas les données brutes du terrain et ne prouve pas que la "
               "collecte a eu lieu : l'audit porte sur la cohérence déclarée, pas sur la réalité de "
               "la collecte.",
        portee="statique"),
    ElementNonVerifiable(
        element="exactitude factuelle des sources citées",
        raison="L'audit peut vérifier qu'une source est annoncée dans le dossier, jamais que son "
               "contenu réel dit ce qu'on lui attribue.",
        portee="statique"),
    ElementNonVerifiable(
        element="originalité et plagiat",
        raison="Aucune comparaison externe (base documentaire, moteur d'anti-plagiat) n'est possible "
               "hors ligne et sans autorisation.",
        portee="statique"),
    ElementNonVerifiable(
        element="qualité rédactionnelle, orthographe, style",
        raison="Ces dimensions relèvent de l'appréciation humaine et de la discipline ; l'agent "
               "n'émet pas d'avis de langue.",
        portee="statique"),
    ElementNonVerifiable(
        element="conformité aux règles locales de l'établissement",
        raison="Les consignes de l'université ou du directeur ne sont pas transmises : toute règle "
               "locale invoquée serait inventée.",
        portee="statique"),
    ElementNonVerifiable(
        element="conformité éthique réelle sur le terrain",
        raison="Consentement, autorisations et protection des participants ne sont pas observables "
               "depuis le dossier.",
        portee="statique"),
    ElementNonVerifiable(
        element="opportunité scientifique du sujet et réception par le jury",
        raison="Il s'agit d'un jugement académique qui appartient au directeur de mémoire et au jury.",
        portee="statique"),
    ElementNonVerifiable(
        element="valeur disciplinaire des choix méthodologiques",
        raison="L'audit vérifie la cohérence interne des choix, pas leur pertinence théorique au "
               "regard d'une discipline donnée.",
        portee="statique"),
)

#: Une étape absente laisse inexplorés tous les liens qui en dépendent.
_LIENS_PAR_ETAPE = {
    "probleme": "les liens entre le sujet et le problème de recherche",
    "problematique": "le découlement de la question de recherche depuis la problématique",
    "question": "la confrontation des objectifs et des résultats à la question de recherche",
    "objectifs": "la couverture des objectifs par les résultats",
    "hypotheses": "l'examinabilité des hypothèses par la méthodologie retenue",
    "methodologie": "l'adéquation des méthodes aux hypothèses et aux objectifs",
    "resultats": "la fidélité de la conclusion aux résultats",
    "conclusion": "la conformité de la conclusion au travail effectivement réalisé",
}


def portee_dynamique(etapes_absentes: list[str]) -> list[ElementNonVerifiable]:
    out: list[ElementNonVerifiable] = []
    for etape in etapes_absentes:
        lien = _LIENS_PAR_ETAPE.get(str(etape).strip().lower())
        if not lien:
            continue
        out.append(ElementNonVerifiable(
            element=f"étape absente : {etape}",
            raison=f"Cette étape n'a pas été transmise : {lien} n'ont pas pu être examinés.",
            portee="dynamique"))
    if etapes_absentes:
        out.append(ElementNonVerifiable(
            element="audit partiel",
            raison=f"Le dossier est incomplet ({len(etapes_absentes)} étape(s) absente(s)) : le "
                   "verdict global porte sur les seuls éléments disponibles.",
            portee="dynamique"))
    return out


def portee_complete(etapes_absentes: list[str],
                    supplement: list[ElementNonVerifiable] | None = None) -> list[ElementNonVerifiable]:
    """Portée statique + dynamique + apports du modèle (dédoublonnés par élément)."""
    vus: set[str] = set()
    out: list[ElementNonVerifiable] = []
    for item in list(PORTEE_STATIQUE) + portee_dynamique(etapes_absentes) + list(supplement or []):
        cle = str(item.element).strip().lower()
        if not cle or cle in vus:
            continue
        vus.add(cle)
        out.append(item)
    return out
