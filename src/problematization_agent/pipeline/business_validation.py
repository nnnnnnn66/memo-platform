"""Validation métier de la sortie : ancrage, anti-fusion, honnêteté, cohérence d'alignement.

Contrôles déterministes. Le plus important : **chaque affirmation théorique doit porter un `doc_id`
du corpus amont ET une citation présente littéralement dans le texte réellement disponible**. Une
affirmation inventée ne franchit pas cette barrière.
"""

import re
import unicodedata

from ..schemas.output import ProblemStatus, ProblematizationOutput
from ..theory import matrix as theory

# Marqueurs des étapes suivantes (produites ailleurs) ou d'une validation non acquise.
FORBIDDEN_MARKERS = [
    "hypothèses de recherche",
    "plan de mémoire",
    "question de recherche définitive",
    "question validée",
    "problématique validée",
    "méthodologie détaillée",
]

# Formules qui NIENT le marqueur ou le renvoient à une étape ultérieure. Un marqueur dans une telle
# phrase n'est PAS une fusion.
#
# Défaut réel (premier parcours de bout en bout, sur un vrai mémoire) : le modèle écrivait
# « cette proposition ne préjuge ni de la question de recherche définitive, ni des objectifs, qui
# relèvent des étapes ultérieures » — c'est-à-dire EXACTEMENT ce que la règle demande — et la
# recherche de sous-chaîne faisait échouer l'étape. Le garde-fou punissait le bon comportement.
NEGATIONS = (
    "ne prejuge", "ne préjuge", "il ne s'agit pas", "n'est pas", "n est pas", "ne sont pas",
    "ne sera", "ne saurait", "pas encore", "provisoire", "a titre de proposition",
    "à titre de proposition", "reste une proposition", "restent des propositions",
    "etape ulterieure", "étape ultérieure", "etapes ulterieures", "étapes ultérieures",
    "releve", "relève", "relevent", "relèvent", "aucun", "aucune", "discutee", "discutée",
    "amendee", "amendée", "ecartee", "écartée", "ne fixe pas", "ne tranche pas",
)


def _phrases(texte: str) -> list[str]:
    """Découpe en phrases : c'est la PHRASE qui porte le sens, pas le marqueur seul."""
    return [phrase.strip() for phrase in re.split(r"(?<=[.!?;:])\s+", texte) if phrase.strip()]


def presente_comme_fige(texte: str, marqueur: str) -> bool:
    """Le marqueur est-il AFFIRMÉ dans une phrase, et non nié ou renvoyé à plus tard ?

    Ne signaler que l'affirmation : une phrase qui dit « elle ne préjuge ni de la question de
    recherche définitive » respecte la règle, elle ne la viole pas.
    """
    for phrase in _phrases(texte):
        if marqueur not in phrase:
            continue
        if any(negation in phrase.lower() for negation in NEGATIONS):
            continue
        return True
    return False


def _statement_fields(output: ProblematizationOutput):
    confrontation = output.literature_confrontation
    for statement in (list(confrontation.modeles_dominants) + list(confrontation.consensus)
                      + list(confrontation.divergences) + list(confrontation.statements)):
        yield "confrontation", statement
    for statement in output.gap.statements:
        yield "gap", statement
    for statement in output.justification.statements:
        yield "justification", statement


def _free_texts(output: ProblematizationOutput) -> str:
    parts = [output.justification.texte, output.problematique_note.texte_complet,
             output.gap.description, output.gap.justification,
             (output.research_question.question or ""), (output.objectives.general or "")]
    parts.extend(output.limits_of_this_note)
    return " ".join(parts)


# --- Source des délimitations du constat (zone, population) ------------------------------------
#
# Même règle que le garde-fou F5 de l'agent Question : une délimitation ajoutée au constat (zone
# géographique, population) doit venir des données de l'étudiant. Si l'agent la reformule ou
# l'enrichit sans le dire, elle est signalée. Elle est ACCEPTÉE si elle est fournie telle quelle, ou
# si elle porte une CITATION EXACTE (entre guillemets) d'un libellé présent dans les données de
# l'étudiant — l'agent attribue alors explicitement à l'étudiant ce qu'il cite.

_CITATION_RES = (
    re.compile(r"«([^»]+)»"),
    re.compile(r"“([^”]+)”"),
    re.compile(r'"([^"]+)"'),
)
_MIN_CITED_CHARS = 4


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip()


def _cited_from_student(value: str, haystack: str) -> bool:
    for pattern in _CITATION_RES:
        for fragment in pattern.findall(str(value or "")):
            normalized = _normalize(fragment)
            if len(normalized) >= _MIN_CITED_CHARS and normalized in haystack:
                return True
    return False


def provided_text(request) -> str:
    """Tout le texte fourni par l'étudiant, imports amont compris (pour tracer une délimitation)."""
    texts = getattr(request, "untrusted_texts", None)
    raw = texts() if callable(texts) else {}
    parts = list(raw.values()) if isinstance(raw, dict) else []
    for attr in ("upstream_subject", "upstream_problem"):
        payload = getattr(request, attr, None)
        if payload is not None and hasattr(payload, "model_dump_json"):
            parts.append(payload.model_dump_json())
    return "\n".join(str(p) for p in parts if p)


_TOKEN_RE = re.compile(r"[a-z0-9]{4,}")


def _anchored(value: str, haystack: str) -> bool:
    """La valeur partage-t-elle AU MOINS un mot significatif avec les données de l'étudiant ?

    Le constat SYNTHÉTISE les entrées : il peut les qualifier (« développeurs d'Abidjan » à partir
    de « développeurs » + « Abidjan »), jamais leur substituer une délimitation étrangère. Un mot
    d'ancrage suffit ; une délimitation entièrement ÉTRANGÈRE (aucun mot commun) est une invention.
    """
    tokens = _TOKEN_RE.findall(value)
    return bool(tokens) and any(token in haystack for token in tokens)


def unsourced_delimitations(mapping, provided: str) -> dict:
    """Délimitations du constat (zone, population) sans ancrage dans les données de l'étudiant.

    Renvoie {champ: valeur} pour chaque délimitation NON traçable. Une valeur est traçable si l'une
    de ces conditions tient :
      - sa forme normalisée figure verbatim dans les données fournies ;
      - elle partage au moins un mot significatif avec les données fournies (ancrage lexical) ;
      - elle porte une CITATION EXACTE (entre guillemets) d'un libellé de l'étudiant — l'agent
        ATTRIBUE alors explicitement à l'étudiant le mot qu'il cite.

    Sans ancrage ni citation, la délimitation ne recoupe AUCUNE donnée de l'étudiant : c'est une
    invention, signalée et jamais acceptée en silence. La règle « attribuée ET citée ⇒ acceptée » ne
    relâche rien : le garde-fou reste strict, il refuse tout ce qui est étranger aux entrées.
    """
    haystack = _normalize(provided)
    out: dict[str, str] = {}
    for field_name, value in (("zone_geographique", getattr(mapping, "zone_geographique", "") or ""),
                              ("population", getattr(mapping, "population", "") or "")):
        value = str(value).strip()
        if not value:
            continue
        normalized = _normalize(value)
        if normalized and normalized in haystack:
            continue
        if _anchored(normalized, haystack):
            continue
        if _cited_from_student(value, haystack):
            continue
        out[field_name] = value
    return out


def validate_semantics(output: ProblematizationOutput, request, index) -> list[str]:
    """Contrôles sur le contenu produit (ancrage, doc_id, anti-fusion, alignement, honnêteté)."""
    violations: list[str] = []
    known_ids = index.doc_ids

    # R1 — fidélité du sujet
    if output.subject_reference.original.strip() != request.subject_text.strip():
        violations.append("R1: subject_reference.original ne correspond pas au sujet reçu")

    # R2 — anti-fusion : rien de la question/des objectifs n'est présenté comme validé
    blob = _free_texts(output).lower()
    for marker in FORBIDDEN_MARKERS:
        if presente_comme_fige(blob, marker):
            violations.append(f"R2: fusion interdite détectée (marqueur « {marker} »)")
    if output.research_question.status.value != "proposed":
        violations.append("R2: la question de recherche doit rester une PROPOSITION (proposed)")
    if output.objectives.status.value != "proposed":
        violations.append("R2: les objectifs doivent rester une PROPOSITION (proposed)")

    # R10 — source des délimitations du constat (zone, population) : une délimitation ajoutée sans
    # ancrage dans les données de l'étudiant, et sans citation exacte, est refusée. Corollaire :
    # une délimitation correctement ATTRIBUÉE et CITÉE (guillemets verbatim) est acceptée.
    added = unsourced_delimitations(output.problem_mapping, provided_text(request))
    if added:
        violations.append(
            "R10: délimitation du constat sans source ("
            + ", ".join(f"{k}={v}" for k, v in added.items())
            + ") : elle doit être fournie par l'étudiant, ou citée mot pour mot par l'agent")

    # R3 — ancrage verbatim obligatoire
    for origin, statement in _statement_fields(output):
        quote = (statement.quote or "").strip()
        if not statement.doc_id:
            violations.append(f"R3: {origin} : affirmation sans doc_id")
            continue
        if statement.doc_id not in known_ids:
            violations.append(f"R3: {origin} : doc_id hors corpus amont ({statement.doc_id})")
            continue
        if not quote:
            violations.append(f"R3: {origin} : affirmation sans citation ({statement.doc_id})")
            continue
        if not index.quote_ok(statement.doc_id, quote):
            violations.append(
                f"R3: {origin} : citation introuvable dans le texte réel de {statement.doc_id} "
                f"(« {quote[:60]}… »)")
        if not statement.anchored:
            violations.append(f"R3: {origin} : affirmation non marquée comme ancrée")

    # R4 — cohérence des compteurs
    if output.bibliography.entries_count != len(output.bibliography.entries):
        violations.append(
            f"R4: entries_count ({output.bibliography.entries_count}) ≠ nombre réel d'entrées "
            f"({len(output.bibliography.entries)})")
    evidence = output.evidence
    if evidence.statements_anchored > evidence.statements_written:
        violations.append("R4: statements_anchored supérieur à statements_written")

    # R5 — bibliographie : uniquement des documents du corpus amont
    for entry in output.bibliography.entries:
        if entry.startswith("[") and "]" in entry:
            doc_id = entry[1:entry.index("]")]
            if doc_id not in known_ids:
                violations.append(f"R5: référence hors corpus amont : {doc_id}")

    # R6 — cohérence de l'amorce d'alignement
    alignment = output.methodological_alignment
    if alignment.matrix_row_id not in theory.BY_ID:
        violations.append(f"R6: matrix_row_id inconnu : {alignment.matrix_row_id!r}")
    else:
        issues = theory.row_coherence_issues(
            alignment.matrix_row_id, alignment.logic.value, alignment.research_type,
            alignment.approach, alignment.techniques)
        if issues:
            violations.append("R6: incohérence d'alignement : " + " ; ".join(issues))
    if alignment.upstream_coherence.value == "divergent" and not alignment.coherence_note.strip():
        violations.append("R6: divergence d'alignement déclarée sans explication")

    # R7 — honnêteté de la production
    if output.status == ProblemStatus.ready_for_verification:
        if not output.gap.description.strip():
            violations.append("R7: production sans gap identifié")
        if not output.limits_of_this_note:
            violations.append("R7: aucune limite déclarée")
        if not any(statement.anchored for _, statement in _statement_fields(output)):
            violations.append("R7: aucune affirmation ancrée dans le texte des documents amont")

    # R8 — l'agent ne s'auto-valide jamais
    if output.validation.verified is True:
        violations.append("R8: l'agent a posé validation.verified=true (réservé au vérificateur)")
    if output.validation.verifier_status != "pending":
        violations.append("R8: verifier_status doit rester 'pending' à la sortie de l'agent")

    return violations


def validate_final(output: ProblematizationOutput) -> list[str]:
    """Contrôles finaux de forme et de cohérence globale."""
    violations: list[str] = []
    if output.status == ProblemStatus.needs_clarification and not output.clarification_questions:
        violations.append("R9: needs_clarification sans question posée à l'étudiant")
    if output.status == ProblemStatus.ready_for_verification:
        if not output.research_question.question.strip():
            violations.append("R9: ready_for_verification sans question de recherche candidate")
        if not output.objectives.general.strip() or len(output.objectives.specifics) < 2:
            violations.append("R9: objectifs candidats incomplets (1 général + 2 à 3 spécifiques)")
    return violations
