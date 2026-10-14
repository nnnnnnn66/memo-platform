"""RECHERCHE DOCUMENTAIRE RÉELLE de l'Agent Sujet.

RENVERSEMENT ASSUMÉ DE LA SPÉCIFICATION D'ORIGINE, à la demande du porteur :

    « l'étudiant vient parce qu'il ne sait rien sur son sujet […] ils sont là pour l'aider, pas
      pour lui poser des questions […] les agents doivent aller chercher l'information »

L'Agent Sujet ne se contente donc plus de questionner : il **va chercher** le contexte du sujet
(travaux existants, définitions, données disponibles, ce qui a déjà été étudié sur ce terrain) et
il **le livre**, avec ses sources — comme le font Perplexity ou Elicit.

Ce qui NE change pas, et qui protège l'étudiant : **rien n'est inventé**. Une affirmation ne peut
citer qu'une source RÉELLEMENT récupérée ici (`source_id` posé par ce module). C'est ce qui rend
« il ne dira pas qu'il n'a pas trouvé » tenable : il cherche pour de vrai, il rapporte ce qu'il a
trouvé, et ce qu'il n'a pas trouvé est décrit comme un manque DE LA RECHERCHE — jamais comme une
question posée à l'étudiant.

Seule exception, et elle est voulue : les informations de TERRAIN (le terrain de l'étudiant, sa
population, son échantillon, ses propres données) ne se trouvent nulle part — c'est le seul point
sur lequel l'agent demande, parce que lui seul les détient.
"""

from dataclasses import dataclass, field

from ..core.errors import PipelineError
from ..core.logging import get_logger

log = get_logger("subject.research")


@dataclass
class SourceRecord:
    """Une référence RÉELLEMENT récupérée auprès d'un fournisseur."""

    source_id: str
    provider: str
    title: str
    url: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    abstract: str = ""
    query: str = ""

    def as_prompt_line(self) -> str:
        """Ligne lisible donnée au modèle. Le `source_id` est ce qu'il doit citer."""
        morceaux = [f"- [source_id: {self.source_id}] {self.title}"]
        if self.authors:
            morceaux.append(", ".join(self.authors[:4]) + (" et al." if len(self.authors) > 4 else ""))
        if self.year:
            morceaux.append(self.year)
        if self.venue:
            morceaux.append(self.venue)
        ligne = " — ".join(morceaux)
        if self.abstract:
            ligne += f"\n    Résumé (extrait) : {self.abstract[:600]}"
        if self.url:
            ligne += f"\n    Lien : {self.url}"
        return ligne


@dataclass
class ResearchResult:
    records: list[SourceRecord] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)
    providers_failed: list[str] = field(default_factory=list)
    network_requests: int = 0
    cache_hits: int = 0
    note: str = ""

    @property
    def bloc_prompt(self) -> str:
        """Bloc injecté dans le message utilisateur. Vide si rien n'a été récupéré."""
        if not self.records:
            return ""
        lignes = [
            "SOURCES RÉELLEMENT RÉCUPÉRÉES POUR CE SUJET (recherche documentaire de la plateforme).",
            "Ce ne sont pas des exemples : ce sont des références existantes, appelées à l'instant.",
            "Tu DOIS t'appuyer dessus et les CITER par leur `source_id`. Tu n'as le droit d'écrire "
            "aucune affirmation issue d'une source qui ne figure pas ci-dessous.",
            "Requêtes exécutées : " + " | ".join(self.queries),
            "",
        ]
        lignes.extend(record.as_prompt_line() for record in self.records)
        return "\n".join(lignes)


_MOTS_VIDES = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "au", "aux", "sur", "dans",
    "pour", "par", "avec", "sans", "chez", "que", "qui", "quoi", "dont", "est", "sont", "cas",
    "effet", "impact", "etude", "étude", "recherche", "memoire", "mémoire", "master", "these",
    "thèse", "analyse", "relation", "entre", "chez", "son", "sa", "ses", "leur", "leurs",
}


def _termes(texte: str, maximum: int = 6) -> list[str]:
    """Mots-clés du sujet, dans l'ordre d'apparition, sans mots vides ni doublons."""
    propres: list[str] = []
    for brut in (texte or "").replace("'", " ").replace("-", " ").split():
        mot = "".join(c for c in brut if c.isalnum())
        if len(mot) < 4 or mot.lower() in _MOTS_VIDES:
            continue
        if mot.lower() not in {m.lower() for m in propres}:
            propres.append(mot)
        if len(propres) >= maximum:
            break
    return propres


def _requetes(termes: list[str], settings, nombre: int) -> list[str]:
    """Requêtes envoyées aux fournisseurs.

    RÈGLE VÉRIFIÉE SUR CE SERVEUR : la plupart des fournisseurs (HAL, theses.fr, OpenAIRE, DOAJ,
    Europe PMC) appliquent un ET sur les requêtes multi-termes — une phrase entière renvoie ZÉRO
    résultat sans erreur. On envoie donc `mot1 OR mot2 OR …` : c'est la seule forme qui ramène
    réellement des travaux proches.
    """
    if not termes:
        return []
    requetes: list[str] = []
    # 1. tous les termes, en OU : le filet le plus large
    requetes.append(" OR ".join(termes))
    # 2. les deux premiers termes seuls : très souvent le croisement qui compte
    if len(termes) >= 2:
        requetes.append(f"{termes[0]} OR {termes[1]}")
    # 3. le terme le plus spécifique (le plus long), seul
    requetes.append(max(termes, key=len))
    vues: list[str] = []
    for requete in requetes:
        if requete and requete not in vues:
            vues.append(requete)
    return vues[:nombre]


def _racine(mot: str) -> str:
    """Radical d'un terme : « immobilières » et « immobilier » doivent matcher ensemble."""
    return mot.lower()[:6]


def _present(terme: str, texte: str) -> bool:
    return _racine(terme) in texte


def _texte_complet(record: dict) -> str:
    """Titre + résumé + revue : un travail pertinent ne se déclare pas seulement dans son titre."""
    morceaux = [str(record.get("title", "")), str(record.get("abstract", "")),
                str(record.get("venue", ""))]
    return " ".join(morceaux).lower()


def _pertinent(record: dict, termes: list[str], coeur: list[str]) -> bool:
    """Filtre de pertinence resserré.

    Défaut réel corrigé : exiger « deux mots de la requête dans le titre » laissait passer des
    travaux hors sujet dès que la requête contenait un toponyme (« Bingerville », « Côte »,
    « Ivoire ») — par exemple un rapport sur l'aviculture à Bingerville pour un sujet sur les
    promotions immobilières. On exige donc en plus qu'un terme du CŒUR du sujet (les concepts,
    pas le terrain) apparaisse réellement.
    """
    if not termes:
        return True
    texte = _texte_complet(record)
    presents = sum(1 for terme in termes if _present(terme, texte))
    if len(termes) >= 2 and presents < 2:
        return False
    if coeur and not any(_present(terme, texte) for terme in coeur):
        return False
    return True


def run(subject_text: str, settings, discipline: str = "", registry=None, fetcher=None,
        cache=None) -> ResearchResult:
    """Interroge les fournisseurs gratuits sans clé et renvoie les références réellement obtenues.

    Ne lève JAMAIS pour un échec réseau : un fournisseur muet est DÉCLARÉ, il ne fait pas échouer
    le travail de l'étudiant (et il ne se transforme jamais en « aucune information n'existe »).
    """
    resultat = ResearchResult()
    if not (settings.sources or {}).get("enabled", False):
        resultat.note = "recherche documentaire désactivée par configuration"
        return resultat

    termes = _termes(subject_text)
    # CŒUR du sujet : les concepts, avant le terrain. Le sujet est très souvent écrit
    # « <phénomène> à <lieu> (<précisions>) » : les tout premiers termes portent le phénomène.
    coeur = termes[:2]
    requetes = _requetes(termes, settings, int(getattr(settings.limits, "max_research_queries", 3)))
    if not requetes:
        resultat.note = "aucun terme exploitable dans le sujet fourni"
        return resultat
    resultat.queries = requetes

    from ..sources.cache import GapCheckCache
    from ..sources.http import ApiFetcher
    from ..sources.registry import Registry

    registry = registry or Registry(settings.providers_file)
    fetcher = fetcher or ApiFetcher(settings.sources or {}, settings.limits,
                                    registry.allowed_hosts())
    cache = cache or GapCheckCache(settings.cache_db, settings.limits.cache_ttl_hours)

    from .discipline import ordonner_fournisseurs

    par_requete = int(getattr(settings.limits, "max_results_per_query", 8))
    vus: set[str] = set()
    limite = int(getattr(settings, "research", {}).get("max_sources", 12) or 12)
    # La FILIÈRE décide de l'ordre de consultation ET du plafond par fournisseur : sans plafond, le
    # premier fournisseur qui répond remplit tout le quota et les autres (les plus pertinents pour
    # la discipline) ne sont jamais atteints.
    par_fournisseur = max(2, limite // 3)
    disponibles = [p.id for p in registry.enabled()]
    ordre = ordonner_fournisseurs(discipline, disponibles)
    par_id = {p.id: p for p in registry.enabled()}

    for identifiant in ordre:
        provider = par_id[identifiant]
        comptes_fournisseur = 0
        search = registry.adapter_module(provider).search
        for requete in requetes:
            try:
                trouve = cache.get(provider.id, requete, par_requete)
                if trouve is None:
                    trouve = search(fetcher, requete, par_requete)
                    cache.set(provider.id, requete, par_requete, trouve)
                if provider.id not in resultat.providers_used:
                    resultat.providers_used.append(provider.id)
            except PipelineError as exc:
                if provider.id not in resultat.providers_failed:
                    resultat.providers_failed.append(provider.id)
                log.info("recherche : fournisseur %s en échec (%s)", provider.id, exc.state.value)
                continue

            for record in trouve or []:
                if not _pertinent(record, termes, coeur):
                    continue
                cle = (record.get("doi") or record.get("title") or "").strip().lower()
                if not cle or cle in vus:
                    continue
                vus.add(cle)
                comptes_fournisseur += 1
                resultat.records.append(SourceRecord(
                    source_id=cle[:160],
                    provider=provider.id,
                    title=str(record.get("title", ""))[:400],
                    url=str(record.get("url", "")),
                    authors=[str(a) for a in (record.get("authors") or [])][:8],
                    year=str(record.get("year", "") or ""),
                    venue=str(record.get("venue", "") or ""),
                    abstract=str(record.get("abstract", "") or ""),
                    query=requete,
                ))
                if len(resultat.records) >= limite or comptes_fournisseur >= par_fournisseur:
                    break
            if len(resultat.records) >= limite:
                break
        if len(resultat.records) >= limite:
            break

    resultat.network_requests = getattr(fetcher, "requests", 0)
    resultat.cache_hits = getattr(cache, "hits", 0)
    resultat.note = (
        f"{len(resultat.records)} référence(s) récupérée(s) via "
        f"{', '.join(resultat.providers_used) or 'aucun fournisseur'}"
        + (f" ; en échec : {', '.join(resultat.providers_failed)}" if resultat.providers_failed else "")
    )
    log.info("recherche sujet terminée : %s", resultat.note)
    return resultat
