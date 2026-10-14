"""RECHERCHE DOCUMENTAIRE DE L'AGENT MÉTHODOLOGIE (étape 9) — adaptée à SA mission.

L'agent 9 ne cherche PAS la littérature du sujet : c'est le travail des étapes 2 à 5. Sa mission est
de construire un **protocole de recherche** (terrain, échantillon, instruments, traitement,
analyse). Il va donc chercher des **références méthodologiques** : échantillonnage, instruments de
collecte, validité, méthodes d'analyse, triangulation — appliquées à la discipline et au terrain
de l'étudiant.

Conséquence directe sur les requêtes : le SUJET seul ne ramène rien d'utile (un sujet porte un
phénomène, pas une méthode). On croise donc :
    - le VOCABULAIRE MÉTHODOLOGIQUE, enrichi par ce que le diagnostic de l'étape 8 a retenu
      (approche, logique, type de recherche, stratégie, collecte, analyse) ;
    - le DOMAINE du sujet (deux ou trois termes), pour que les références portent sur des méthodes
      réellement applicables à ce travail — pas de méthodologie médicale pour un mémoire de
      géographie.

Comme partout : les références sont RÉELLEMENT récupérées et citables par `source_id` ; aucune
n'est inventée, et un manque se déclare comme constat de recherche, jamais comme question rendue à
l'étudiant (seul le TERRAIN — son terrain, son accès, ses contraintes — se demande).
"""

from dataclasses import dataclass, field

from ..core.errors import PipelineError
from ..core.logging import get_logger

log = get_logger("methode.research")

# Vocabulaire méthodologique de base : c'est le CŒUR de la recherche de cet agent.
_METHODES = [
    "échantillonnage", "questionnaire", "entretien semi-directif", "observation participante",
    "analyse de contenu", "triangulation", "méthodologie de recherche", "étude de cas",
    "analyse qualitative", "analyse statistique", "validité", "fiabilité",
]

# Ce que le diagnostic de l'étape 8 a retenu → vocabulaire de requête (on traduit, on ne recopie pas).
_DIAGNOSTIC_VERS_REQUETE = {
    "approche": {"qualitatif": "recherche qualitative", "quantitatif": "recherche quantitative",
                 "mixte": "méthodes mixtes",
                 "hypothetico": "méthode hypothético-déductive",
                 "inductif": "raisonnement inductif", "abductif": "raisonnement abductif"},
    "type_recherche": {"descriptif": "étude descriptive", "explicatif": "étude explicative",
                       "exploratoire": "étude exploratoire", "experimental": "plan expérimental"},
    "collecte": {"questionnaire": "questionnaire", "entretien": "entretien",
                 "observation": "observation", "documentaire": "analyse documentaire",
                 "sondage": "enquête par sondage"},
    "analyse": {"contenu": "analyse de contenu", "statistique": "analyse statistique",
                "thematique": "analyse thématique", "discours": "analyse du discours",
                "comparative": "analyse comparative"},
}


@dataclass
class SourceRecord:
    """Une référence méthodologique RÉELLEMENT récupérée."""

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
        if not self.records:
            return ""
        lignes = [
            "RÉFÉRENCES MÉTHODOLOGIQUES RÉELLEMENT RÉCUPÉRÉES (recherche documentaire de la "
            "plateforme, faite à l'instant pour CE travail).",
            "Ce ne sont pas des exemples : ce sont des travaux existants sur les méthodes dont tu "
            "as besoin. Appuie-toi dessus et cite-les par leur `source_id`.",
            "Aucune affirmation ne peut s'appuyer sur une référence absente de cette liste : une "
            "référence inventée est refusée, comme un chiffre inventé.",
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
    "donnees", "données", "métier", "terrain",
}


def _termes(texte: str, maximum: int = 6) -> list[str]:
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


def _vocabulaire_du_diagnostic(request) -> list[str]:
    """Ce que l'étape 8 a retenu, traduit en vocabulaire de recherche documentaire."""
    try:
        categories = request.diagnostic_categories()
    except Exception:  # noqa: BLE001 — diagnostic absent : la recherche ne doit pas échouer
        return []
    trouve: list[str] = []
    for nom, table in _DIAGNOSTIC_VERS_REQUETE.items():
        entrees = categories.get(nom)
        for entree in (entrees if isinstance(entrees, list) else [entrees]):
            if not isinstance(entree, dict):
                continue
            texte = f"{entree.get('proposition', '')} {entree.get('code', '')}".lower()
            for cle, requete in table.items():
                if cle in texte and requete not in trouve:
                    trouve.append(requete)
    return trouve


def _requetes(domaine: list[str], methode: list[str], nombre: int) -> list[str]:
    """Requêtes en `mot1 OR mot2 …` : la plupart des fournisseurs appliquent un ET sur les requêtes
    multi-termes et renvoient ZÉRO résultat sans erreur (piège vérifié sur HAL, theses.fr, DOAJ)."""
    socle = (methode or _METHODES[:6])[:5]
    requetes: list[str] = [" OR ".join(socle)]
    if domaine:
        requetes.append(" OR ".join(socle[:3] + domaine[:2]))
        requetes.append(" OR ".join(domaine))
    uniques: list[str] = []
    for requete in requetes:
        if requete and requete not in uniques:
            uniques.append(requete)
    return uniques[:nombre]


def _racine(mot: str) -> str:
    return mot.lower()[:6]


# Mots qui trahissent un travail de MÉTHODE dans un titre. Liste volontairement plus large que le
# vocabulaire de requête : on cherche ce qui existe, pas seulement ce qu'on a pensé à demander.
_MOTS_METHODE_TITRE = [
    "échantillonnage", "échantillon", "questionnaire", "entretien", "enquête", "sondage",
    "observation", "analyse de contenu", "analyse qualitative", "analyse quantitative",
    "analyse statistique", "analyse thématique", "analyse de données", "méthodologie",
    "méthode", "protocole", "triangulation", "étude de cas", "focus group", "expérimentation",
    "validité", "fiabilité", "grille", "codage", "échelle de mesure", "collecte de données",
]


def _titre(record: dict) -> str:
    return str(record.get("title", "")).lower()


def _pertinent(record: dict, domaine: list[str], methodes: list[str]) -> bool:
    """EXIGENCE : le TITRE doit nommer une méthode.

    Défaut réel corrigé : juger sur titre + résumé laissait passer des travaux hors sujet — un
    résumé d'agronomie contient « analyse » et « promotion » (au sens de « promotion d'une
    culture »), donc il satisfaisait toutes les conditions. Un travail de méthode le dit dans son
    titre ; le reste est du bruit.

    Le DOMAINE n'est PAS un filtre mais un ORDRE : un manuel d'échantillonnage reste utile même
    s'il ne parle pas du sujet de l'étudiant, alors qu'un travail de méthode de SA discipline est
    plus directement applicable. On garde donc les deux, et le tri place la discipline devant
    (voir `run`) — c'est ce qui permet de retrouver « L'approche qualitative et quantitative dans
    l'enquête de terrain » sur un sujet de géographie.
    """
    titre = _titre(record)
    return any(_racine(mot) in titre for mot in _MOTS_METHODE_TITRE)


def run(request, settings, registry=None, fetcher=None, cache=None) -> ResearchResult:
    """Interroge les fournisseurs gratuits sans clé et renvoie les références méthodologiques.

    Ne lève jamais pour un échec réseau : un fournisseur muet est DÉCLARÉ (`providers_failed`).
    """
    resultat = ResearchResult()
    if not (settings.sources or {}).get("enabled", False):
        resultat.note = "recherche documentaire désactivée par configuration"
        return resultat

    from .discipline import profil as profil_discipline

    filiere = profil_discipline(getattr(request, "discipline", "") or "")
    domaine = _termes(getattr(request, "subject_text", "") or "")
    # Le vocabulaire de méthode est enrichi par celui de la FILIÈRE : les instruments et les
    # méthodes d'analyse ne portent pas le même nom en santé, en droit ou en gestion.
    methode = list(_vocabulaire_du_diagnostic(request) or _METHODES[:5])
    for mot in filiere.vocabulaire:
        if mot not in methode:
            methode.append(mot)
    requetes = _requetes(domaine, methode, int(getattr(settings.limits, "max_research_queries", 3)))
    if not requetes:
        resultat.note = "aucune requête exploitable"
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

    par_requete = int(getattr(settings.limits, "max_results_per_query", 8) or 8)
    limite = int((getattr(settings, "research", {}) or {}).get("max_sources", 12) or 12)
    vus: set[str] = set()
    par_fournisseur = max(2, limite // 3)
    disponibles = [p.id for p in registry.enabled()]
    par_id = {p.id: p for p in registry.enabled()}

    for identifiant in ordonner_fournisseurs(getattr(request, "discipline", "") or "", disponibles):
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
                log.info("recherche méthodologique : %s en échec (%s)", provider.id, exc.state.value)
                continue

            for record in trouve or []:
                if not _pertinent(record, domaine, methode):
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
    # Les références de la DISCIPLINE passent devant : plus directement applicables au travail.
    resultat.records.sort(key=lambda r: 0 if any(_racine(m) in r.title.lower() for m in domaine) else 1)
    resultat.note = (
        f"{len(resultat.records)} référence(s) méthodologique(s) récupérée(s) via "
        f"{', '.join(resultat.providers_used) or 'aucun fournisseur'}"
        + (f" ; en échec : {', '.join(resultat.providers_failed)}" if resultat.providers_failed else "")
    )
    log.info("recherche méthodologique terminée : %s", resultat.note)
    return resultat
