"""Contrôles déterministes de l'étape 11 (K1–K9).

Le fond reste au vérificateur indépendant : ici, seuls des défauts OBJECTIFS, constatables par le
programme. Chaque contrôle est calibré pour ne jamais refuser une conclusion juste (leçon F5/M4/R2/R7).

Règle structurante de l'étape : **la conclusion ne produit aucun résultat nouveau**. Toute affirmation
centrale doit renvoyer à un résultat de l'étape 10, par son identifiant, et aucun chiffre ne peut
apparaître s'il ne vient pas des calculs de l'étape 10.
"""

import re

from . import numeric_guard

_CAUSALITY = [r"\bcausalit[eé]\b", r"\bprovoque\b", r"\bentra[iî]ne\b", r"\bdétermine\b",
              r"\bengendre\b", r"\bimpacte\b", r"\bexplique (la|les|le)\b"]
_NEGATION = ["sans", "pas", "aucun", "aucune", "jamais", "non", "ni", "exclut", "exclure", "écarte",
             "écarter", "refuse", "impossible", "ne", "n'", "interdit", "proscrit", "évite"]
_CONFIRMED = [r"hypoth[eè]se\s*(?:H?\d+)?\s*(?:est\s*)?confirm", r"\bhypoth[eè]ses? (est|sont) valid",
              r"\bd[ée]montre que\b", r"\bpreuve (que|de)\b"]
#: Marqueurs de perspective employés dans une section déclarée « constat ».
_PERSPECTIVE_MARKERS = [r"à l['’]avenir", r"des recherches futures", r"il serait (utile|intéressant)",
                        r"pourrait être (étudié|exploré|approfondi)", r"perspectives? de recherche"]
#: Citations bibliographiques : « (Nom, 2020) » ou « Nom (2020) ».
_CITATION = re.compile(r"\(([A-ZÉÈÀÂÎÔÛ][\w'’\-]+(?: et al\.)?),?\s*(\d{4})\)")
_IMPERSONAL_CITATION = re.compile(r"\b([A-ZÉÈÀÂÎÔÛ][\w'’\-]{2,})\s*\((\d{4})\)")


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).lower()


def _negation_near(text: str, match: re.Match, before: int = 4, after: int = 3) -> bool:
    window = " " + " ".join(text[:match.start()].split()[-before:]) + " " \
             + " ".join(text[match.end():].split()[:after]) + " "
    return any(f" {neg} " in window for neg in _NEGATION)


def _all_text(synthesis, plan, draft) -> str:
    chunks: list[str] = [synthesis.reponse_question.reponse, synthesis.reponse_question.portee]
    for bilan in (synthesis.bilan_objectifs or []):
        chunks += [bilan.objectif, bilan.commentaire]
    for bilan in (synthesis.bilan_hypotheses or []):
        chunks += [bilan.hypothese, bilan.justification]
    for section in (plan.sections or []):
        chunks += [section.titre, section.fonction, section.contenu_prevu]
    for section in (draft.sections or []):
        chunks += [section.titre, section.contenu, section.justification]
    chunks += list(draft.apports_scientifiques or [])
    chunks += list(draft.apports_pratiques or [])
    chunks += list(draft.limites or [])
    chunks += list(draft.perspectives or [])
    return _squash(" \n ".join(c for c in chunks if c))


def run_checks(request, synthesis, plan, draft) -> list[str]:
    """Retourne la liste des violations (vide = conforme)."""
    violations: list[str] = []
    ids = request.computed_ids()
    text = _all_text(synthesis, plan, draft)
    plan_only = synthesis.plan_seulement or not ids

    # K1 — traçabilité : toute affirmation centrale doit citer un résultat EXISTANT de l'étape 10.
    references: list[tuple[str, str]] = []
    for section in (draft.sections or []):
        references += [(r, section.titre) for r in section.resultats or []]
    references += [(r, "réponse à la question") for r in synthesis.reponse_question.etayage or []]
    for bilan in (synthesis.bilan_objectifs or []):
        references += [(r, bilan.objectif) for r in bilan.resultats or []]
    if references and not plan_only:
        for reference, ou in references:
            if str(reference).strip() not in ids:
                violations.append(
                    f"K1 : l'affirmation portée par « {ou} » renvoie à « {reference} », qui n'existe "
                    "pas parmi les résultats vérifiés de l'étape 10.")
                break
    if not plan_only and not references:
        violations.append(
            "K1 : la conclusion ne cite AUCUN résultat de l'étape 10. Chaque affirmation centrale "
            "doit renvoyer au résultat qui la justifie (champ `resultats`).")

    # K2 — anti-invention : aucun chiffre hors des résultats de l'étape 10 et des entrées.
    sources = list(request.untrusted_texts().values())
    sources += [request.effective_question(), request.effective_general_objective()]
    sources += list(request.effective_specific_objectives())
    sources += list(request.effective_hypotheses())
    sources += [str(r.get("valeur", "")) for r in
                (request.upstream_results.computed_resultats() if request.upstream_results else [])]
    allowed = {v for v in request.computed_valeurs() if v}
    allowed |= numeric_guard_numbers(sources)
    pieces = {titre: contenu for titre, contenu in
              [(s.titre or f"section {i}", s.contenu) for i, s in enumerate(draft.sections or [], 1)]}
    pieces["reponse"] = synthesis.reponse_question.reponse
    pieces["portee"] = synthesis.reponse_question.portee
    pieces["apports"] = " ".join(list(draft.apports_scientifiques or [])
                                 + list(draft.apports_pratiques or []))
    pieces["limites"] = " ".join(draft.limites or [])
    pieces["perspectives"] = " ".join(draft.perspectives or [])
    for label, contenu in pieces.items():
        hits = numeric_guard.check_texts({label: contenu}, allowed)
        if hits:
            violations.extend(h.replace("Q2 :", "K2 :", 1) if h.startswith("Q2") else h
                              for h in hits[:2])
            break

    # K3 — le statut d'une hypothèse ne peut PAS contredire l'examen de l'étape 10.
    examines = request.upstream_results.hypotheses_examinees() if request.upstream_results else []
    etape10 = {_squash(h.get("hypothese", "")): str(h.get("statut", "")).strip()
               for h in examines}
    for bilan in (synthesis.bilan_hypotheses or []):
        statut = getattr(bilan.statut, "value", bilan.statut)
        cle = _squash(bilan.hypothese)
        for formulation, statut10 in etape10.items():
            if cle and (cle in formulation or formulation in cle) and statut10:
                if statut10 == "non_examinable" and statut in ("soutenue", "non_soutenue"):
                    violations.append(
                        "K3 : l'hypothèse « " + bilan.hypothese[:80] + " » est présentée comme "
                        f"« {statut} » alors que l'étape 10 l'a jugée NON EXAMINABLE avec les données "
                        "disponibles.")
                break
        if len(violations) > 4:
            break

    # K4 — causalité affirmée sans dispositif.
    protocole = request.methodology_protocol()
    dispositif = _squash(" ".join(str(protocole.get(key, "")) for key in
                                  ("type_recherche", "strategie", "approche")))
    experimental = bool(re.search(r"exp[ée]rimental|quasi[- ]exp|essai|contrôle", dispositif))
    if not experimental:
        for pattern in _CAUSALITY:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not _negation_near(text, match):
                violations.append(
                    f"K4 : la conclusion affirme une relation causale (« {match.group(0)} ») alors que "
                    "le dispositif ne le permet pas. Parlez d'association, ou écartez explicitement "
                    "la causalité.")
                break

    # K5 — une hypothèse ne peut pas être présentée comme CONFIRMÉE.
    for pattern in _CONFIRMED:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            violations.append(
                f"K5 : « {match.group(0)} » présente une hypothèse comme CONFIRMÉE. La conclusion "
                "rend compte de ce que les résultats soutiennent ou non, sans trancher une "
                "démonstration.")
            break

    # K6 — aucune référence bibliographique inventée.
    # ATTENTION : la détection se fait sur le texte NON mis en minuscules (une citation commence par
    # une majuscule) — `text` est écrasé en minuscules pour les autres contrôles.
    sources_dispo = " ".join(
        (request.upstream_literature.sources_litterature() if request.upstream_literature else []))
    brut = " ".join([s.contenu or "" for s in draft.sections or []]
                    + [b.commentaire or "" for b in synthesis.bilan_objectifs or []])
    citations = [m.group(0) for m in _CITATION.finditer(brut)] + \
                [m.group(0) for m in _IMPERSONAL_CITATION.finditer(brut)]
    if citations and not sources_dispo.strip():
        violations.append(
            "K6 : la conclusion cite des références (« " + citations[0] + " ») alors qu'aucune source "
            "bibliographique n'est disponible dans le dossier. Ne citez que ce qui existe.")
    elif citations:
        for citation in citations:
            nom = re.sub(r"\s*\(?\d{4}\)?", "", citation).strip(" (,)")
            if nom and _squash(nom) not in _squash(sources_dispo):
                violations.append(
                    "K6 : la référence « " + citation + " » ne figure pas parmi les sources "
                    "disponibles (étape 3).")
                break

    # K7 — constat / interprétation / perspective distingués.
    for section in (draft.sections or []):
        niveau = getattr(section.niveau, "value", section.niveau)
        contenu = _squash(section.contenu)
        if niveau == "constat" and any(re.search(p, contenu) for p in _PERSPECTIVE_MARKERS):
            violations.append(
                "K7 : la section « " + (section.titre or "")[:60] + " » est déclarée comme un CONSTAT "
                "mais énonce une perspective. Marquez-la `perspective`.")
            break

    # K8 — sans résultats, la production reste un PLAN (jamais une conclusion rédigée).
    if plan_only and (draft.sections or []):
        violations.append(
            "K8 : aucun résultat vérifié n'est disponible, mais une conclusion RÉDIGÉE est produite. "
            "Sans résultats, seul un plan de conclusion peut être proposé.")

    # K9 — aucun résultat nouveau : les identifiants cités proviennent tous de l'étape 10.
    essentiels = [str(r).strip() for r in synthesis.resultats_essentiels or []]
    inconnus = [r for r in essentiels if r and r not in ids]
    if inconnus and not plan_only:
        violations.append(
            "K9 : la synthèse retient des résultats inexistants (« " + ", ".join(inconnus[:3]) +
            " »). Seuls les résultats de l'étape 10 peuvent être synthétisés.")

    return violations


def numeric_guard_numbers(sources: list[str]) -> set[str]:
    """Nombres présents dans les entrées (années, effectifs déclarés, valeurs citées)."""
    allowed: set[str] = set()
    for text in sources:
        for token in re.findall(r"\d+(?:[.,]\d+)?", str(text or "")):
            allowed |= {token, token.replace(".", ","), token.replace(",", ".")}
    allowed |= {str(n) for n in range(0, 13)}
    return {v for v in allowed if v}
