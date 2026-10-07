"""Matrice décisionnelle d'alignement théorique (SPEC §4.4A) — stockée en DONNÉES.

Le diagnostic de l'agent doit pointer une ligne de cette matrice ; la validation métier vérifie la
cohérence entre les indicateurs repérés et la démarche proposée. Une combinaison mixte est acceptée
si elle est explicitement justifiée.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MatrixRow:
    id: str
    label: str
    indicators: list[str]
    reasoning_logic: str
    research_type: str
    approach: str
    techniques: list[str] = field(default_factory=list)


# Transcription fidèle de la matrice de la SPEC §4.4A.
MATRIX: list[MatrixRow] = [
    MatrixRow(
        id="explore_phenomenon",
        label="Comprendre un phénomène peu étudié",
        indicators=["comment", "quels sont les mécanismes", "explorer", "peu étudié", "exploratoire"],
        reasoning_logic="inductive",
        research_type="exploratory",
        approach="qualitative",
        techniques=["entretiens semi-directifs", "observation", "analyse de contenu"],
    ),
    MatrixRow(
        id="verify_theory",
        label="Vérifier une théorie existante",
        indicators=["dans quelle mesure", "vérifier l'applicabilité", "confirmer", "valider la théorie"],
        reasoning_logic="deductive",
        research_type="confirmatory",
        approach="quantitative",
        techniques=["enquête par questionnaire", "modélisation statistique"],
    ),
    MatrixRow(
        id="test_hypothesis",
        label="Tester une hypothèse",
        indicators=["quel est l'impact", "quels sont les effets", "tester l'influence", "hypothèse"],
        reasoning_logic="hypothetico_deductive",
        research_type="explanatory",
        approach="quantitative",
        techniques=["questionnaire fermé", "échantillonnage probabiliste", "régressions"],
    ),
    MatrixRow(
        id="plausible_explanation",
        label="Chercher l'explication la plus plausible d'un phénomène",
        indicators=["pourquoi observe-t-on", "expliquer le décalage", "contradiction", "paradoxe"],
        reasoning_logic="abductive",
        research_type="mixed",
        approach="mixed_methods",
        techniques=["triangulation des données", "études de cas comparatives"],
    ),
    MatrixRow(
        id="measure_relation",
        label="Mesurer une relation entre variables",
        indicators=["quelle est la corrélation", "lien entre", "relation entre", "association"],
        reasoning_logic="hypothetico_deductive",
        research_type="correlational",
        approach="quantitative",
        techniques=["analyses descriptives", "analyses inférentielles"],
    ),
    MatrixRow(
        id="explore_experiences",
        label="Explorer les expériences ou perceptions des acteurs",
        indicators=["comment les acteurs", "vécu", "perception", "donner du sens", "expérience"],
        reasoning_logic="inductive",
        research_type="phenomenological",
        approach="qualitative",
        techniques=["entretiens approfondis", "récits de vie", "focus groups"],
    ),
    MatrixRow(
        id="compare_situations",
        label="Comparer deux situations ou populations",
        indicators=["comparer", "variations entre", "différences entre", "entre deux"],
        reasoning_logic="mixed",
        research_type="comparative",
        approach="mixed_methods",
        techniques=["grilles d'analyse comparatives", "tests d'hypothèses"],
    ),
    MatrixRow(
        id="evaluate_intervention",
        label="Évaluer l'effet d'une intervention",
        indicators=["efficacité de", "impact du programme", "évaluation de l'intervention",
                    "avant/après"],
        reasoning_logic="hypothetico_deductive",
        research_type="experimental",
        approach="quantitative",
        techniques=["mesures pré/post-test", "groupes témoins", "indicateurs"],
    ),
]

BY_ID = {row.id: row for row in MATRIX}

# Alias acceptés pour le type de recherche (le modèle peut produire une variante proche).
_RAW_RESEARCH_TYPE_ALIASES = {
    "explicative": "explanatory",
    "confirmatoire": "confirmatory",
    "exploratoire": "exploratory",
    "descriptive": "descriptive",
    "correlationnelle": "correlational",
    "phenomenologique": "phenomenological",
    "comprehensive": "phenomenological",
    "experimentale": "experimental",
    "quasi-experimentale": "quasi_experimental",
    "mixte": "mixed",
    "comparative": "comparative",
}

_RAW_LOGIC_ALIASES = {
    "inductif": "inductive", "inductive": "inductive",
    "deductif": "deductive", "déductif": "deductive", "deductive": "deductive",
    "hypothetico-deductif": "hypothetico_deductive",
    "hypothético-déductif": "hypothetico_deductive",
    "abductif": "abductive", "abductive": "abductive",
    "mixte": "mixed", "mixed": "mixed",
}


def _key(value: str) -> str:
    """Clé de recherche tolérante : minuscules, sans accents, tirets normalisés."""
    import unicodedata

    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.replace(" ", "_").replace("-", "_")


# Les alias sont indexés par clé normalisée : « Hypothético-déductif » et « hypothetico_deductif »
# tombent ainsi sur la même entrée.
LOGIC_ALIASES = {_key(key): value for key, value in _RAW_LOGIC_ALIASES.items()}
RESEARCH_TYPE_ALIASES = {_key(key): value for key, value in _RAW_RESEARCH_TYPE_ALIASES.items()}


def normalize_logic(value: str) -> str:
    return LOGIC_ALIASES.get(_key(value), _key(value) or "mixed")


def normalize_research_type(value: str) -> str:
    return RESEARCH_TYPE_ALIASES.get(_key(value), _key(value) or "mixed")


def detect_rows(text: str) -> list[MatrixRow]:
    """Repère les lignes de matrice dont un indicateur sémantique apparaît dans le texte."""
    haystack = (text or "").lower()
    hits = []
    for row in MATRIX:
        if any(indicator in haystack for indicator in row.indicators):
            hits.append(row)
    return hits


def row_coherence_issues(row_id: str, reasoning_logic: str, research_type: str,
                         approach: str, techniques: list[str]) -> list[str]:
    """Contrôle la cohérence entre la ligne de matrice déclarée et la démarche proposée.

    Une combinaison mixte est acceptée : le contrôle ne signale que les incohérences franches
    (par exemple logique inductive + approche quantitative sans justification).
    """
    issues: list[str] = []
    row = BY_ID.get(row_id)
    if row is None:
        return [f"ligne de matrice inconnue : {row_id!r}"]

    logic = normalize_logic(reasoning_logic)
    research_type = normalize_research_type(research_type)
    if research_type not in {row.research_type, "mixed", "descriptive"} and row.research_type != "mixed":
        # tolérance : « comparative » et « corrélationnelle » peuvent cohabiter
        if not {research_type, row.research_type} & {"comparative", "correlational"}:
            issues.append(
                f"type de recherche déclaré « {research_type} » ≠ type attendu de la ligne "
                f"« {row.research_type} »"
            )
    if approach not in (row.approach, "mixed_methods"):
        if not (row.approach == "mixed_methods" or approach == "mixed_methods"):
            issues.append(
                f"approche déclarée « {approach} » ≠ approche attendue de la ligne "
                f"« {row.approach} »"
            )
    if logic != row.reasoning_logic and logic != "mixed" and row.reasoning_logic != "mixed":
        issues.append(
            f"logique déclarée « {logic} » ≠ logique attendue de la ligne « {row.reasoning_logic} »"
        )
    if not techniques:
        issues.append("aucune technique déclarée")
    return issues
