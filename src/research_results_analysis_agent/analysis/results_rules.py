"""Contrôles déterministes de l'étape 10 (Q1–Q9).

Le fond reste au vérificateur indépendant : ici, seuls des défauts OBJECTIFS, constatables par le
programme. Chaque contrôle est calibré pour ne jamais refuser une production juste (leçon F5/M4/R2/R7).
"""

import re

from . import numeric_guard

#: Mots de causalité (Q5) — jamais une simple sous-chaîne : la fenêtre de NÉGATION est mesurée en MOTS.
_CAUSALITY = [r"\bcausalit[eé]\b", r"\bprovoque\b", r"\bentra[iî]ne\b", r"\bdétermine\b",
              r"\bengendre\b", r"\bimpacte\b", r"\bexplique (la|les|le)\b"]
_NEGATION = ["sans", "pas", "aucun", "aucune", "jamais", "non", "ni", "exclut", "exclure", "écarte",
             "écarter", "refuse", "impossible", "ne", "n'", "interdit", "proscrit", "évite"]
#: Marqueurs de conclusion générale (Q9) — rôle de l'étape 11.
_CONCLUSION = [r"\ben conclusion\b", r"\bnotre étude (démontre|prouve|conclut)\b",
               r"\bon peut (donc )?affirmer que\b", r"\bcela prouve que\b",
               r"\ben définitive,? (cette|notre) (étude|recherche)\b"]
_CONFIRMED = [r"hypoth[eè]se\s*(?:H?\d+)?\s*(?:est\s*)?confirm", r"\bhypoth[eè]ses? (est|sont) valid",
              r"\bpreuve (que|de)\b", r"\bdémontre que\b"]


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).lower()


def _negation_near(text: str, match: re.Match, before: int = 4, after: int = 3) -> bool:
    window = " " + " ".join(text[:match.start()].split()[-before:]) + " " \
             + " ".join(text[match.end():].split()[:after]) + " "
    return any(f" {neg} " in window for neg in _NEGATION)


def _all_text(plan, interpretation, draft) -> str:
    chunks: list[str] = []
    for resultat in (plan.resultats or []):
        chunks += [resultat.observation, resultat.objectif] + list(resultat.limites or [])
    for examen in (plan.hypotheses or []):
        chunks += [examen.hypothese, examen.justification]
    for lecture in (interpretation.lectures or []):
        chunks += [lecture.observation, lecture.interpretation] + list(lecture.autres_explications or [])
    for tableau in (interpretation.tableaux or []):
        chunks += [tableau.titre, tableau.lecture]
    for figure in (interpretation.figures or []):
        chunks += [figure.titre, figure.lecture]
    for comparison in (interpretation.comparaison_litterature or []):
        chunks += [comparison.lien, comparison.source]
    for section in (draft.sections or []):
        chunks.append(section.contenu)
    chunks += list(draft.synthese_pour_conclusion or [])
    return _squash(" \n ".join(c for c in chunks if c))


def run_checks(request, computed, plan, interpretation, draft, inventory) -> list[str]:
    """Retourne la liste des violations (vide = conforme)."""
    violations: list[str] = []
    text = _all_text(plan, interpretation, draft)
    ids = computed.ids()

    # Q1 — un résultat affirmé doit renvoyer à un calcul réel.
    for resultat in (plan.resultats or []):
        reference = str(resultat.id_resultat or "").strip()
        if not reference:
            violations.append(
                "Q1 : un résultat est affirmé sans référence à un calcul (champ `id_resultat` vide). "
                "Chaque affirmation chiffrée doit citer le résultat calculé correspondant.")
            break
        if reference not in ids:
            violations.append(
                f"Q1 : le résultat affirmé renvoie à « {reference} », qui n'existe pas parmi les "
                "calculs réalisés.")
            break

    # Q2 — anti-invention : liste blanche numérique.
    texts = {"analyse": text,
             "confiance": "", "titre": ""}
    pieces = dict(texts)
    pieces["tableaux"] = " ".join(t.lecture for t in interpretation.tableaux or [])
    pieces["figures"] = " ".join(f.lecture for f in interpretation.figures or [])
    pieces["synthese"] = " ".join(draft.synthese_pour_conclusion or [])
    sources = list(request.untrusted_texts().values())
    sources += [str(r.valeur) for r in computed.resultats]
    sources.append(request.subject_text)
    sources.append(" ".join(request.effective_specific_objectives()))
    sources.append(request.effective_general_objective())
    allowed = _whitelist(computed, request)
    for label, piece in pieces.items():
        violations.extend(numeric_guard.check_texts({label: piece}, allowed)[:4])
        if len(violations) > 6:
            break

    # Q3 — une hypothèse « soutenue » exige des résultats calculés.
    for examen in (plan.hypotheses or []):
        if getattr(examen.statut, "value", examen.statut) == "soutenue" and not examen.resultats:
            violations.append(
                "Q3 : une hypothèse est déclarée SOUTENUE sans résultat calculé associé. Indiquez les "
                "résultats qui la soutiennent, ou requalifiez-la (non soutenue / non examinable).")
            break

    # Q4 — aucune hypothèse ne peut être déclarée « confirmée » par cette étape.
    for pattern in _CONFIRMED:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            violations.append(
                f"Q4 : « {match.group(0)} » présente une hypothèse comme CONFIRMÉE. Une analyse "
                "descriptive ne confirme pas une hypothèse : parlez de résultat compatible, de "
                "soutien partiel ou de non-examen.")
            break

    # Q5 — causalité affirmée sans dispositif (fenêtre de négation mesurée en mots).
    protocole = request.methodology_protocol()
    dispositif = _squash(" ".join(str(protocole.get(key, "")) for key in
                                  ("type_recherche", "strategie", "approche")))
    experimental = bool(re.search(r"exp[ée]rimental|quasi[- ]exp|essai|contrôle", dispositif))
    if not experimental:
        for pattern in _CAUSALITY:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not _negation_near(text, match):
                violations.append(
                    f"Q5 : le document affirme une relation causale (« {match.group(0)} ») alors que "
                    "le dispositif ne le permet pas. Parlez d'association, ou écartez explicitement "
                    "la causalité.")
                break

    # Q6 — observation et interprétation séparées.
    for lecture in (interpretation.lectures or []):
        if not str(lecture.observation or "").strip() or not str(lecture.interpretation or "").strip():
            violations.append(
                "Q6 : une lecture ne sépare pas l'OBSERVATION (le fait) de l'INTERPRÉTATION (ce que "
                "l'on en propose). Les deux champs sont obligatoires.")
            break

    # Q7 — données manquantes / doublons non déclarés.
    manquants_reels = _missing_counts(request)
    if manquants_reels and not (inventory.manquants or request.__dict__.get("_manquants")):
        if not inventory.manquants:
            violations.append(
                "Q7 : des valeurs manquantes existent dans les données mais ne sont pas déclarées "
                "dans l'inventaire (SPEC §10.4 : jamais masquées).")

    # Q8 — une citation doit exister dans le corpus fourni.
    corpus = _squash(" ".join(request.untrusted_texts().values()))
    for lecture in (interpretation.lectures or []):
        for extrait in re.findall(r"«([^»]{10,200})»", lecture.interpretation or ""):
            if _squash(extrait) not in corpus:
                violations.append(
                    "Q8 : un extrait entre guillemets ne figure pas dans les données ou documents "
                    "fournis. Ne jamais fabriquer une citation.")
                break

    # Q9 — la conclusion générale n'appartient pas à cette étape.
    for pattern in _CONCLUSION:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(
                "Q9 : le document rédige une CONCLUSION GÉNÉRALE, qui relève de l'étape 11. "
                "Limitez-vous aux résultats et à leur analyse.")
            break

    return violations


def _missing_counts(request) -> int:
    total = 0
    for dataset in request.datasets:
        if dataset.format != "csv" or not str(dataset.contenu or "").strip():
            continue
        from . import data_engine
        total += sum(v.get("manquants", 0) for v in data_engine.profile(dataset.contenu)["variables"])
    return total


def _whitelist(computed, request) -> set[str]:
    from . import data_engine
    sources = list(request.untrusted_texts().values())
    sources.append(request.subject_text)
    sources.append(request.effective_general_objective())
    sources.extend(request.effective_specific_objectives())
    sources.extend(request.effective_hypotheses())
    return data_engine.numeric_whitelist(
        [r.model_dump() for r in computed.resultats], sources)
