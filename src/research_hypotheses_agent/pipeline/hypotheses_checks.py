"""Étape [4] — contrôles déterministes des hypothèses (SPEC §7, §9.4, §10).

Décision cohérente avec les hypothèses produites, hypothèse ≠ question ≠ objectif ≠ fait établi,
causalité non établie signalée, caractère examinable, justification traçable, redondance. Ces
contrôles sont CODÉS.
"""

from ..analysis import hypothesis_rules
from ..schemas.hypotheses import DecisionCode


def apply(output, request) -> list[str]:
    violations: list[str] = []
    decision = output.hypotheses_decision
    hypotheses = list(output.research_hypotheses)
    formulations = [(h.formulation or "").strip() for h in hypotheses]

    # H1 — cohérence entre la décision et les hypothèses présentes.
    if decision == DecisionCode.recommended and not [f for f in formulations if f]:
        violations.append("H1: hypothèses recommandées mais aucune hypothèse formulée")
    if decision == DecisionCode.not_required and [f for f in formulations if f]:
        violations.append(
            "H1: décision 'HYPOTHESES_NOT_REQUIRED' mais des hypothèses sont présentes")
    if decision == DecisionCode.require_clarification and (output.clarification_questions == []
            and output.status.value != "needs_clarification"):
        violations.append(
            "H1: décision 'HYPOTHESES_REQUIRE_CLARIFICATION' sans question de clarification")

    question = (request.effective_question() or "").strip().lower().rstrip("? ")
    objectives = [(o or "").strip().lower().rstrip("? ") for o in
                  ([request.effective_general_objective()] + request.effective_specific_objectives())]
    context = " ".join(filter(None, [request.all_provided_text(),
                                     request.effective_question(),
                                     request.effective_general_objective()]))

    for index, h in enumerate(hypotheses, start=1):
        text = (h.formulation or "").strip()
        if not text:
            violations.append(f"H2: hypothèse {index} sans formulation")
            continue
        # H2 — une hypothèse N'EST PAS une question ni un objectif.
        if hypothesis_rules.looks_like_question(text):
            violations.append(f"H2: hypothèse {index} est une question, pas une proposition")
        if hypothesis_rules.looks_like_objective(text):
            violations.append(
                f"H2: hypothèse {index} est un objectif (verbe d'action en tête), pas une hypothèse")
        # H3 — aucune conclusion présentée comme un fait établi.
        facts = hypothesis_rules.presupposed_fact_hits(text)
        if facts:
            violations.append(
                f"H3: hypothèse {index} présente une conclusion comme un fait établi")
        # H4 — causalité non établie.
        causal = hypothesis_rules.causal_hits(text)
        ungrounded = [c for c in causal if not hypothesis_rules.causal_is_justified(c, context)]
        if ungrounded:
            violations.append(
                f"H4: hypothèse {index} pose une causalité non établie ("
                + ", ".join(sorted(set(ungrounded)))
                + ") : préfère une association, ou justifie la causalité")
        # H5 — examinable et suffisamment précise.
        if not hypothesis_rules.is_examinable(text, h.required_data):
            violations.append(
                f"H5: hypothèse {index} n'est pas examinable (aucune relation ni données requises)")
        if hypothesis_rules.is_too_short(text):
            violations.append(f"H5: hypothèse {index} trop vague (trop courte)")
        # H6 — justification traçable.
        if not (h.justification or "").strip() and not h.sources:
            violations.append(f"H6: hypothèse {index} sans justification traçable")
        # H8 — anti-fusion : l'hypothèse n'est ni la question ni un objectif (texte identique).
        if question and text.lower().rstrip("? ") == question:
            violations.append(f"H8: hypothèse {index} recopie la question (fusion interdite)")
        if text.lower().rstrip("? ") in objectives:
            violations.append(f"H8: hypothèse {index} recopie un objectif (fusion interdite)")

    # H7 — redondance entre hypothèses.
    for i, j in hypothesis_rules.duplicate_hypotheses(formulations):
        violations.append(f"H7: hypothèses {i} et {j} se recouvrent (redondance)")

    return violations
