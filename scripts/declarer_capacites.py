"""Déclare la capacité de chaque agent : ajoute « GET /capabilities » à son API.

Leçon du lab (AGENT → API → ORCHESTRATEUR) : un agent doit pouvoir répondre à
**WHO ARE YOU / WHAT CAN YOU DO / WHERE ARE YOU / ARE YOU ONLINE**. `/health` dit déjà qui il est
et qu'il répond ; `/capabilities` dit ce qu'il SAIT FAIRE et ce dont il a besoin pour travailler.

L'orchestrateur n'a ainsi plus besoin de devinier : il interroge, il lit, il vérifie.

Les entrées requises sont lues dans `config/settings-orchestrateur.yaml` — SOURCE UNIQUE : la
déclaration de l'agent ne peut pas diverger de la carte du parcours.

Usage :  python scripts/declarer_capacites.py            (applique)
         python scripts/declarer_capacites.py --verifier  (contrôle seulement)
"""

import pathlib
import re
import sys

import yaml

RACINE = pathlib.Path(__file__).resolve().parents[1]
CONFIG = RACINE / "config" / "settings-orchestrateur.yaml"

# Rôle et capacités de chaque agent (le reste est lu dans la carte du parcours).
DECLARATIONS = {
    "subject_agent": (
        "Cadre le sujet de mémoire et détecte les informations manquantes (QUOI/QUI/OÙ/QUAND).",
        ["sujet", "cadrage", "clarification"], False),
    "research_problem_agent": (
        "Formule le problème de recherche et mène une recherche documentaire déterministe.",
        ["probleme_recherche", "recherche_documentaire", "clarification"], True),
    "literature_review_agent": (
        "Interroge les fournisseurs scientifiques, télécharge et LIT les textes intégraux, "
        "sélectionne le corpus, ancre les citations et produit la bibliographie.",
        ["revue_litterature", "recherche_documentaire", "telechargement_pdf", "lecture_pdf",
         "bibliographie", "matrice_comparative", "synthese_critique"], True),
    "problematization_agent": (
        "Construit la problématique, la matrice théorique et vérifie le manque (gap check).",
        ["problematique", "construction_theorique", "gap_check"], True),
    "research_question_agent": (
        "Produit LA question de recherche validée — jamais fusionnée avec la problématique.",
        ["question_recherche"], False),
    "research_objectives_agent": (
        "Produit l'objectif général et les objectifs spécifiques, avec contrôle de faisabilité.",
        ["objectifs", "faisabilite"], False),
    "research_hypotheses_agent": (
        "Recommande ou écarte des hypothèses de recherche (le silence est une réponse valable).",
        ["hypotheses"], False),
    "methodology_diagnostic_agent": (
        "Diagnostique l'orientation méthodologique (approche, logique, type, stratégie, collecte, "
        "analyse) selon les règles M1-M7.",
        ["diagnostic_methodologique", "regles_m1_m7"], False),
    "methodology_agent": (
        "Rédige la méthodologie : protocole, instruments, matrice de cohérence.",
        ["methodologie", "protocole", "instruments", "matrice_coherence"], False),
    "research_results_analysis_agent": (
        "Calcule les résultats par le CODE (jamais par le modèle) et les interprète.",
        ["resultats", "analyse", "calcul_deterministe"], False),
    "research_conclusion_agent": (
        "Rédige la conclusion : synthèse fidèle du travail réellement réalisé.",
        ["conclusion", "synthese"], False),
    "research_coherence_verifier": (
        "Vérifie la cohérence TRANSVERSALE du dossier complet et dit ce qu'il ne peut pas vérifier.",
        ["verification_globale", "coherence_transversale"], False),
}

BLOC = '''

@router.get("/capabilities")
async def capabilities() -> dict:
    """Ce que cet agent SAIT FAIRE, et ce dont il a besoin pour travailler.

    Répond aux quatre questions que l'orchestrateur doit pouvoir poser :
    WHO ARE YOU (`agent`) — WHAT CAN YOU DO (`capacites`) — WHAT DO YOU NEED (`entrees_requises`)
    — ARE YOU ONLINE (`/health`). Déclaration en DONNÉES : l'orchestrateur la LIT, il ne la devine pas.
    """
    return _CAPACITES
'''


def declarations() -> dict:
    """Construit la déclaration de chaque agent à partir de la carte du parcours."""
    carte = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    par_agent = {}
    for etape in carte["etapes"]:
        role, capacites, reseau = DECLARATIONS.get(
            etape["agent"], (etape.get("libelle", ""), [], False))
        par_agent[etape["agent"]] = {
            "agent": etape["agent"],
            "etape": etape["numero"],
            "nom": etape["libelle"],
            "role": role,
            "capacites": capacites,
            "entrees_requises": sorted(etape.get("upstream") or {}),
            "necessite_reseau": reseau,
            "portillon_humain": True,
            "version": "1.0",
        }
    return par_agent


def _bloc_donnees(declaration: dict) -> str:
    lignes = ["_CAPACITES = {"]
    for cle, valeur in declaration.items():
        lignes.append(f"    {cle!r}: {valeur!r},")
    lignes.append("}")
    return "\n".join(lignes)


def traiter(chemin: pathlib.Path, declaration: dict, verifier: bool) -> str:
    texte = chemin.read_text(encoding="utf-8")
    if '"/capabilities"' in texte:
        return "déjà déclaré"
    if verifier:
        return "MANQUANT"

    # On insère la déclaration juste avant la fonction `health`, puis l'endpoint juste après elle.
    ancre = '@router.get("/health")'
    if ancre not in texte:
        return "ANCRE INTROUVABLE"
    texte = texte.replace(ancre, _bloc_donnees(declaration) + "\n\n\n" + ancre, 1)

    # Fin de la fonction health : la ligne suivante qui commence par @router.
    suite = re.search(r'(@router\.get\("/health"\)\n(?:.*\n)*?)\n(@router\.)', texte)
    if not suite:
        return "FIN DE FONCTION INTROUVABLE"
    texte = texte[:suite.end(1)] + BLOC + texte[suite.end(1):]
    chemin.write_text(texte, encoding="utf-8")
    return "déclaré"


def main() -> int:
    verifier = "--verifier" in sys.argv
    par_agent = declarations()
    resultats = {}
    for agent, declaration in sorted(par_agent.items()):
        chemin = RACINE / "src" / agent / "api" / "routes.py"
        if not chemin.exists():
            resultats[agent] = "FICHIER ABSENT"
            continue
        resultats[agent] = traiter(chemin, declaration, verifier)
    largeur = max(len(a) for a in resultats)
    for agent, etat in resultats.items():
        print(f"  {agent:<{largeur}}  {etat}")
    manquants = [a for a, e in resultats.items() if e in ("MANQUANT", "FICHIER ABSENT",
                                                          "ANCRE INTROUVABLE",
                                                          "FIN DE FONCTION INTROUVABLE")]
    if manquants:
        print(f"\n{len(manquants)} agent(s) à traiter : {', '.join(manquants)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
