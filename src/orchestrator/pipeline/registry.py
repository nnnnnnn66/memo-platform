"""Registre des agents : l'orchestrateur les INTERROGE, il ne les devine pas.

Leçon du lab (AGENT → API → ORCHESTRATEUR) : chaque agent expose son identité et ses capacités, et
l'orchestrateur doit pouvoir répondre aux quatre questions avant de lui confier du travail :

- **WHO ARE YOU ?**      → `GET /capabilities` → `agent`, `nom`, `role`
- **WHAT CAN YOU DO ?**  → `GET /capabilities` → `capacites`
- **WHAT DO YOU NEED ?** → `GET /capabilities` → `entrees_requises`
- **ARE YOU ONLINE ?**   → `GET /health`

Deux usages :
1. **Avant de lancer une étape** : refuser proprement si l'agent est éteint, au lieu de laisser
   échouer l'appel avec une erreur technique.
2. **Contrôle de cohérence** : si un agent se déclare à une autre étape que celle prévue par la
   carte, ou lui manque une entrée que la carte lui fournit, c'est SIGNALÉ — un désaccord entre la
   carte et les agents est exactement ce qui casse silencieusement une chaîne.

Le résultat est mis en cache quelques secondes : on n'interroge pas douze services à chaque clic.
"""

import json
import time
import urllib.error
import urllib.request

from ..core.config import Settings

CACHE_SECONDES = 30
_cache: dict = {"quand": 0.0, "registre": None}


def _lire(url: str, timeout: float) -> dict:
    requete = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        return json.loads(reponse.read().decode("utf-8", errors="replace") or "{}")


def ecarts(etape, declaration: dict) -> list:
    """Désaccords entre ce qu'un agent DÉCLARE et ce que la carte du parcours prévoit.

    Un désaccord carte ↔ agent est exactement ce qui casse une chaîne EN SILENCE : il doit être
    signalé, jamais absorbé.
    """
    problemes: list = []
    etape_declaree = declaration.get("etape")
    try:
        if etape_declaree is not None and int(etape_declaree) != etape.numero:
            problemes.append(
                f"déclare l'étape {etape_declaree} alors que la carte prévoit l'étape {etape.numero}")
    except (TypeError, ValueError):
        problemes.append(f"déclare une étape illisible ({etape_declaree!r})")
    attendues = set(etape.upstream)
    fournies = {str(entree) for entree in (declaration.get("entrees_requises") or [])}
    non_prevues = fournies - attendues
    if non_prevues:
        problemes.append(
            "attend des entrées que la carte ne fournit pas : " + ", ".join(sorted(non_prevues)))
    return problemes


def interroger_agent(etape, hote: str, timeout: float = 5.0) -> dict:
    """Interroge un agent : en ligne ou non, et sa déclaration de capacités."""
    fiche = {
        "agent": etape.agent,
        "etape": etape.numero,
        "libelle": etape.libelle,
        "adresse": f"{hote}:{etape.port}",
        "en_ligne": False,
        "etat_sante": "",
        "capacites": [],
        "role": "",
        "nom_declare": "",
        "entrees_requises": [],
        "necessite_reseau": None,
        "probleme": "",
    }
    try:
        sante = _lire(f"http://{hote}:{etape.port}/health", timeout)
        fiche["etat_sante"] = str(sante.get("status", ""))
        fiche["en_ligne"] = fiche["etat_sante"].lower() in ("healthy", "ok", "online")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as erreur:
        fiche["probleme"] = f"injoignable ({type(erreur).__name__})"
        return fiche

    try:
        declaration = _lire(f"http://{hote}:{etape.port}/capabilities", timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as erreur:
        # En ligne mais ne se déclare pas : capacité INCONNUE — on le dit, on ne l'invente pas.
        fiche["probleme"] = f"se déclare mal ({type(erreur).__name__})"
        return fiche

    fiche["capacites"] = [str(c) for c in (declaration.get("capacites") or [])]
    fiche["role"] = str(declaration.get("role") or "")
    fiche["nom_declare"] = str(declaration.get("nom") or "")
    fiche["entrees_requises"] = [str(e) for e in (declaration.get("entrees_requises") or [])]
    fiche["necessite_reseau"] = declaration.get("necessite_reseau")
    fiche["etape_declaree"] = declaration.get("etape")

    # Contrôle de cohérence carte ↔ agent (un désaccord doit être VISIBLE, pas silencieux).
    ecarts_detectes = ecarts(etape, declaration)
    if ecarts_detectes:
        fiche["probleme"] = " ; ".join(ecarts_detectes)
    return fiche


def registre(settings: Settings, forcer: bool = False, interrogateur=None) -> list:
    """Registre complet des agents (une fiche par étape), mis en cache quelques secondes.

    `interrogateur(etape)` peut être injecté par les tests : aucun réseau n'est alors nécessaire.
    """
    maintenant = time.monotonic()
    if (not forcer and interrogateur is None and _cache["registre"] is not None
            and maintenant - _cache["quand"] < CACHE_SECONDES):
        return _cache["registre"]

    question = interrogateur or (lambda etape: interroger_agent(etape, settings.hote))
    fiches = [question(etape) for etape in settings.etapes]
    if interrogateur is None:
        _cache["registre"] = fiches
        _cache["quand"] = maintenant
    return fiches


def fiche_de_etape(settings: Settings, numero: int, interrogateur=None) -> dict | None:
    """Fiche d'UN agent — interrogé directement (pas de cache) : c'est un contrôle juste avant
    de lui confier du travail, on veut l'état réel, pas un état vieux de trente secondes."""
    etape = settings.par_numero.get(numero)
    if etape is None:
        return None
    if interrogateur is not None:
        return interrogateur(etape)
    return interroger_agent(etape, settings.hote)


def agents_hors_ligne(settings: Settings, interrogateur=None) -> list:
    return [fiche for fiche in registre(settings, interrogateur=interrogateur)
            if not fiche["en_ligne"]]


def reinitialiser_cache() -> None:
    """Vide le cache (tests et changement d'état volontaire)."""
    _cache["registre"] = None
    _cache["quand"] = 0.0
