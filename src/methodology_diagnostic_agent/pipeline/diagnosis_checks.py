"""Étape [4] — contrôles déterministes du diagnostic (SPEC §7, §10, §13).

Distinction des catégories, causalité sans dispositif adéquat, compatibilité approche ↔ analyse,
conditions/faisabilité, traitement des hypothèses. Ces contrôles sont CODÉS.
"""

from ..analysis import methodology_rules as rules


def apply(output, request) -> list[str]:
    violations: list[str] = []
    diag = output.diagnosis

    # M1 — codes canoniques des catégories.
    for name, choice in (("approche", diag.approche), ("logique", diag.logique),
                         ("type_recherche", diag.type_recherche), ("strategie", diag.strategie)):
        if choice.code and not rules.is_known(choice.code, name):
            violations.append(f"M1: {name}.code « {choice.code} » hors énumération canonique")

    # M2 — tout choix porte une justification.
    for name, choice in (("approche", diag.approche), ("logique", diag.logique),
                         ("type_recherche", diag.type_recherche), ("strategie", diag.strategie)):
        if not (choice.justification or "").strip():
            violations.append(f"M2: {name} sans justification")

    # M3 — anti-fusion : les catégories ne sont pas interchangeables (textes distincts).
    pairs = [("approche", diag.approche.proposition), ("logique", diag.logique.proposition),
             ("type_recherche", diag.type_recherche.proposition),
             ("strategie", diag.strategie.proposition)]
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            if rules.same_text(pairs[i][1], pairs[j][1]):
                violations.append(
                    f"M3: « {pairs[i][0]} » et « {pairs[j][0]} » sont formulés de façon identique — "
                    "ces catégories ne sont PAS interchangeables")

    # M4 — causalité : aucune lecture causale sans dispositif expérimental (SPEC §10.8-10.9).
    texts = [diag.articulation, diag.coherence_question,
             diag.approche.proposition, diag.type_recherche.proposition,
             diag.strategie.proposition]
    texts += [c.proposition for c in diag.collecte] + [c.proposition for c in diag.analyse]
    causal = []
    for text in texts:
        causal.extend(rules.causal_hits(text))
    if causal and not rules.causality_is_justified(diag.strategie.code):
        violations.append(
            "M4: une causalité est évoquée sans dispositif expérimental (stratégie = "
            f"« {diag.strategie.code or 'non précisée'} ») : parler d'association, ou justifier un "
            "dispositif permettant la causalité")

    # M5 — compatibilité approche ↔ collecte ET approche ↔ analyse.
    for issue in rules.collecte_incompatible(diag.approche.code,
                                             [c.proposition for c in diag.collecte]):
        violations.append("M5: " + issue)
    for issue in rules.analysis_incompatible(diag.approche.code,
                                             [c.proposition for c in diag.analyse]):
        violations.append("M5: " + issue)

    # M6 — la stratégie et la collecte exposent leurs conditions.
    if not diag.strategie.conditions:
        violations.append("M6: la stratégie proposée n'expose aucune condition requise")
    for index, choice in enumerate(diag.collecte, start=1):
        if not (choice.proposition or "").strip():
            violations.append(f"M6: technique de collecte {index} vide")

    # M7 — hypothèses : si le dossier en contient, le diagnostic dit lesquelles il peut examiner.
    if request.effective_hypotheses() and not output.hypotheses_examined:
        violations.append(
            "M7: le dossier contient des hypothèses mais le diagnostic n'indique pas lesquelles la "
            "méthodologie permettra d'examiner (hypotheses_examined est vide)")

    return violations
