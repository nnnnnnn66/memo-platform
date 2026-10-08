"""Étape [7] — contrôle déterministe de l'intention (SPEC §9.2).

L'intention doit découler de la problématique. Si plusieurs intentions sont possibles et modifieraient
substantiellement la question, on le signale (portillon humain) au lieu de trancher arbitrairement.
"""

from ..analysis import intent as intent_module

# Intentions dont la coexistence change substantiellement la question posée. Volontairement
# restreint aux divergences STRUCTURANTES (exemple canonique de la SPEC §15 : « mesurer une relation »
# vs « comprendre les expériences »). Expliquer et comprendre coexistent souvent sans ambiguïté.
_CONFLICTING_PAIRS = [
    {"mesurer", "comprendre"},
    {"mesurer", "explorer"},
    {"evaluer", "explorer"},
]


def check(intention, comprehension, problematic_text: str) -> dict:
    """Retourne {issues, ambiguous, clarification_question}."""
    issues: list[str] = []
    key = intent_module.normalize_intent(intention.intention)

    if not intent_module.is_known(key):
        issues.append("intention non reconnue dans l'enum canonique")
    if key == "autre" and not intention.justification.strip():
        issues.append("intention « autre » sans justification")

    alternatives = [intent_module.normalize_intent(a)
                    for a in intention.alternatives if str(a).strip()]
    alternatives = [a for a in alternatives if a != key]

    ambiguous = False
    clarification = ""
    for a, b in _CONFLICTING_PAIRS:
        both = {a, b}
        if key in both and (both & set(alternatives)):
            ambiguous = True
            clarification = (
                f"Votre problématique peut se lire de deux façons : « {intent_module.LABELS[a]} » ou "
                f"« {intent_module.LABELS[b]} ». Ces deux orientations conduisent à des questions "
                "différentes. Pouvez-vous préciser ce que vous cherchez principalement à établir ?")
            break

    return {"issues": issues, "ambiguous": ambiguous, "clarification_question": clarification}
