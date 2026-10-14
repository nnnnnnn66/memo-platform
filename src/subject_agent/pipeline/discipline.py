"""PROFIL DE DISCIPLINE — l'agent sait POUR QUELLE FILIÈRE il travaille.

Demande du porteur : « les étudiants viennent de plusieurs filières différentes, donc [les agents]
doivent pouvoir chercher les trucs pour chaque filière, comprendre ce qu'ils font et leur donner
leur résultat propre à leur domaine — pas inventer. »

Ce que fait ce module : il traduit la discipline DÉCLARÉE (texte libre de l'étudiant, ou déduite du
département) en un profil exploitable par la recherche documentaire :

  - **fournisseurs prioritaires** : la médecine se documente dans Europe PMC et OpenAlex ; une thèse
    française de droit ou de gestion se trouve dans theses.fr, HAL et DOAJ ; l'ingénierie et les
    sciences exactes dans OpenAlex, Crossref et DataCite.
  - **vocabulaire de requête** : la langue et le lexique changent (un mémoire de santé se cherche
    aussi en anglais ; une filière francophone se cherche d'abord en français).
  - **domaine normalisé**, pour que le prompt de l'agent parle à l'étudiant dans SA discipline.

Ce module NE DÉCIDE PAS du fond : il oriente la recherche. Aucune information n'en sort — il ne
produit que des mots-clés et un ordre de consultation.
"""

from dataclasses import dataclass, field

# Toutes les familles connues, avec leurs fournisseurs prioritaires (dans l'ordre).
# Les identifiants sont ceux de `sources/providers.yaml` : un identifiant inconnu est ignoré.
PROFILS: dict[str, dict] = {
    "sante": {
        "libelle": "Santé / Médecine / Biologie",
        "fournisseurs": ["europepmc", "openalex", "crossref", "doaj", "openaire"],
        "vocabulaire": ["systematic review", "clinical study", "cohort", "prevalence",
                        "échantillon", "protocole d'étude", "statistical analysis"],
        "bilingue": True,
    },
    "droit": {
        "libelle": "Droit / Science politique",
        "fournisseurs": ["theses_fr", "hal", "doaj", "openaire", "openalex"],
        "vocabulaire": ["analyse juridique", "jurisprudence", "méthode comparative",
                        "sources du droit", "étude de cas"],
        "bilingue": False,
    },
    "gestion": {
        "libelle": "Sciences de gestion / Économie",
        "fournisseurs": ["theses_fr", "hal", "openalex", "crossref", "repec", "doaj"],
        "vocabulaire": ["étude de cas", "questionnaire", "analyse stratégique", "sondage",
                        "données de panel", "analyse financière"],
        "bilingue": True,
    },
    "sciences_sociales": {
        "libelle": "Sciences sociales / Sociologie / Anthropologie",
        "fournisseurs": ["theses_fr", "hal", "openalex", "openaire", "doaj"],
        "vocabulaire": ["entretien semi-directif", "observation participante", "analyse de contenu",
                        "échantillonnage raisonné", "étude de terrain"],
        "bilingue": False,
    },
    "geographie": {
        "libelle": "Géographie / Aménagement / Environnement",
        "fournisseurs": ["hal", "theses_fr", "openaire", "datacite", "openalex", "doaj"],
        "vocabulaire": ["télédétection", "analyse spatiale", "occupation du sol",
                        "enquête de terrain", "système d'information géographique"],
        "bilingue": False,
    },
    "education": {
        "libelle": "Sciences de l'éducation",
        "fournisseurs": ["theses_fr", "hal", "doaj", "openalex", "openaire"],
        "vocabulaire": ["recherche-action", "analyse des pratiques", "questionnaire", "entretien",
                        "étude de cas"],
        "bilingue": False,
    },
    "ingenierie": {
        "libelle": "Ingénierie / Sciences exactes / Informatique",
        "fournisseurs": ["openalex", "crossref", "datacite", "arxiv", "doaj"],
        "vocabulaire": ["expérimentation", "benchmark", "protocole expérimental",
                        "analytical model", "performance evaluation"],
        "bilingue": True,
    },
    "lettres": {
        "libelle": "Lettres / Langues / Arts",
        "fournisseurs": ["theses_fr", "hal", "doaj", "openaire", "openalex"],
        "vocabulaire": ["analyse littéraire", "corpus", "analyse de discours", "lecture critique"],
        "bilingue": False,
    },
    "general": {
        "libelle": "Discipline non identifiée",
        "fournisseurs": ["openalex", "crossref", "hal", "theses_fr", "doaj", "openaire", "datacite"],
        "vocabulaire": [],
        "bilingue": True,
    },
}

# Repérage de la famille à partir du texte de discipline fourni par l'étudiant.
_INDICES: dict[str, list[str]] = {
    "sante": ["medecin", "médecin", "sante", "santé", "infirmier", "pharmac", "biolog",
              "epidemio", "épidémio", "clinique", "veterina", "vétérina", "kinesi", "kinési"],
    "droit": ["droit", "juridique", "science politique", "politique", "relations internationales"],
    "gestion": ["gestion", "economi", "économi", "commerce", "finance", "banque", "market",
                "comptab", "management", "entreprise", "ressources humaines"],
    "sciences_sociales": ["sociolog", "anthropolog", "psycholog", "sciences sociales",
                          "communication", "travail social"],
    "geographie": ["geograph", "géograph", "environnement", "amenagement", "aménagement",
                   "urbanis", "urbain", "territoire", "cartograph", "geolog", "géolog"],
    "education": ["education", "éducation", "pedagog", "pédagog", "enseignement", "didactique",
                  "formation", "scolaire"],
    "ingenierie": ["ingenieur", "ingénieur", "informatique", "genie", "génie", "physique", "chimie",
                   "mathemat", "mathémat", "statistiqu", "electron", "électron", "mecanique",
                   "mécanique", "reseau", "réseau", "logiciel", "data", "intelligence artificielle"],
    "lettres": ["lettre", "langue", "litterature", "littérature", "art", "histoire", "philosoph",
                "cinema", "cinéma", "music", "musicolog"],
}


@dataclass(frozen=True)
class ProfilDiscipline:
    famille: str
    libelle: str
    fournisseurs: list[str] = field(default_factory=list)
    vocabulaire: list[str] = field(default_factory=list)
    bilingue: bool = False

    @property
    def reconnue(self) -> bool:
        return self.famille != "general"


def _normalise(texte: str) -> str:
    import unicodedata
    sans_accent = "".join(c for c in unicodedata.normalize("NFD", (texte or "").lower())
                          if unicodedata.category(c) != "Mn")
    return sans_accent


def profil(discipline: str) -> ProfilDiscipline:
    """Profil de recherche déduit de la discipline déclarée (texte libre, donc jamais fiable).

    Sans discipline reconnue, on retourne le profil « general » : tous les fournisseurs, aucun
    vocabulaire ajouté — on ne devine pas une discipline, et une recherche générale reste honnête.
    """
    normalisee = _normalise(discipline)
    for famille, indices in _INDICES.items():
        if any(_normalise(indice) in normalisee for indice in indices):
            config = PROFILS[famille]
            return ProfilDiscipline(
                famille=famille,
                libelle=config["libelle"],
                fournisseurs=list(config["fournisseurs"]),
                vocabulaire=list(config["vocabulaire"]),
                bilingue=bool(config.get("bilingue", False)),
            )
    config = PROFILS["general"]
    return ProfilDiscipline(famille="general", libelle=config["libelle"],
                            fournisseurs=list(config["fournisseurs"]),
                            vocabulaire=list(config["vocabulaire"]),
                            bilingue=bool(config.get("bilingue", False)))


def ordonner_fournisseurs(discipline: str, disponibles: list[str]) -> list[str]:
    """Ordonne les fournisseurs disponibles selon le profil : les plus pertinents d'abord.

    L'ORDRE COMPTE VRAIMENT : le premier fournisseur qui répond remplit le quota de références. Sur
    une filière santé sans Europe PMC en tête, l'agent ramènerait des publications généralistes à la
    place des revues cliniques. Les fournisseurs absents de `providers.yaml` sont ignorés (et non
    inventés) ; ceux du profil absents de la liste disponible sont simplement sautés.
    """
    ordre = profil(discipline).fournisseurs
    rang = {identifiant: i for i, identifiant in enumerate(ordre)}
    return sorted(disponibles, key=lambda identifiant: (rang.get(identifiant, len(ordre)), identifiant))
