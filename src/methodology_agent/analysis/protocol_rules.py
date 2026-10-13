"""Contrôles déterministes de l'étape 9 (P1–P9).

Ces contrôles ne jugent PAS le fond (c'est le rôle du vérificateur indépendant) : ils attrapent des
défauts OBJECTIFS que le programme peut constater seul. Chacun est calibré pour ne jamais bloquer une
campagne saine — leçon du projet : un contrôle déterministe mal calibré (F5, M4, R2, R7) refuse une
sortie pourtant juste, et le modèle ne peut pas « corriger » ce qui n'est pas faux.

Surfaces de NÉGATION : mesurées en MOTS autour du terme (jamais une simple sous-chaîne) : une phrase
qui ÉCARTE la causalité ne doit pas déclencher le contrôle de causalité.
"""

import re

from ..schemas.protocol import EchantillonnageType, SourceTaille, StatutAffirmation

# --- P1 : une opération PRÉVUE ne doit jamais être énoncée au passé -----------------------------
_PAST_COLLECTION = [
    r"\bnous avons (collect|administr|réalis|men|interrog|observ|enregistr|distribu)",
    r"\b(les|des) (entretiens|questionnaires|observations|données|enquêtes)\b[^.\n]{0,40}"
    r"\b(ont été|a été|étaient) (réalis|collect|administr|men|conduit|effectu)",
    r"\bl['’]enquête a été (menée|réalisée|conduite)",
    r"\b(le|la) (terrain|collecte|enquête) (est|a été) (terminé|achevé|réalisé)",
    r"\bj['’]ai (collecté|interrogé|observé|administré|mené)",
]
# --- P7 : causalité affirmée --------------------------------------------------------------------
_CAUSALITY = [r"\bcausalit[eé]\b", r"\bprovoque\b", r"\bentra[iî]ne\b", r"\bdétermine\b",
              r"\bexplique (la|les|le)\b", r"\bmodère\b", r"\bimpacte\b", r"\bengendre\b"]
#: Fenêtre de négation mesurée en MOTS : 4 avant / 3 après le terme.
_NEGATION = ["sans", "pas", "aucun", "aucune", "jamais", "non", "ni", "exclut", "exclure", "écarte",
             "écarter", "refuse", "impossible", "ne", "n'", "interdit", "proscrit", "évite"]
# --- P2 : techniques de terrain -------------------------------------------------------------
_TERRAIN_TECHNIQUES = ["questionnaire", "entretien", "observation", "sondage", "focus group"]
# --- P6 : inférence statistique -------------------------------------------------------------
_INFERENTIAL = ["test statistique", "khi", "chi-2", "chi2", "régression", "anova", "corrélation",
                "test de student", "test t", "significati", "inférentiel", "inférentielle"]
# --- P8 : exigence d'établissement inventée -------------------------------------------------
_INSTITUTION = [r"l['’]universit[ée] (exige|impose|demande|requiert)",
                r"(le|les) r[èe]glement[s]? de l['’][ée]tablissement (exige|impose)",
                r"selon (les|nos) normes? de l['’][ée]tablissement",
                r"conform[ée]ment au r[èe]glement de l['’]universit[ée]",
                r"comme l['’]exige (le|la) (universit[ée]|facult[ée]|d[ée]partement)"]


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).lower()


def _hit(patterns, text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _negation_near(text: str, term_match: re.Match, before: int = 4, after: int = 3) -> bool:
    """Vrai si le terme est ÉCARTÉ par une négation proche (fenêtre mesurée en mots)."""
    words = text[:term_match.start()].split()
    context_before = " ".join(words[-before:])
    words_after = text[term_match.end():].split()
    context_after = " ".join(words_after[:after])
    window = f" {context_before} {context_after} "
    return any(f" {neg} " in window or window.startswith(f" {neg} ") for neg in _NEGATION)


def _all_text(protocol, draft) -> str:
    chunks = [protocol.terrain, protocol.strategie, protocol.type_recherche, protocol.approche]
    for row in (protocol.donnees or []):
        chunks += [row.categorie, row.description]
    for row in (protocol.analyses or []):
        chunks += [row.nom, row.objet] + list(row.conditions or [])
    for row in (protocol.variables_indicateurs or []):
        chunks += [row.nom, row.nature]
    for section in (draft.sections if draft else []):
        chunks.append(section.contenu)
    return _squash(" \n ".join(c for c in chunks if c))


def run_checks(request, protocol, matrix, draft, analysis) -> list[str]:
    """Retourne la liste des violations (vide = conforme)."""
    violations: list[str] = []
    text = _all_text(protocol, draft)

    # P1 — opération présentée comme réalisée sans preuve.
    proofs = [p for p in (request.realise_preuves or []) if str(p).strip()]
    declared_past = [s for s in (draft.sections if draft else [])
                     if s.statut == StatutAffirmation.realise]
    if declared_past and not proofs:
        violations.append(
            "P1 : le document présente des opérations comme RÉALISÉES sans preuve fournie par "
            "l'étudiant. Marquez-les « prévu » ou fournissez la preuve (autorisation, données, "
            "compte rendu).")
    else:
        for pattern in _PAST_COLLECTION:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not _negation_near(text, match, before=3, after=1):
                # On tolère une mention au passé si l'étudiant a fourni une preuve.
                if not proofs:
                    violations.append(
                        "P1 : une collecte ou une analyse est présentée au PASSÉ alors que le "
                        "protocole est une prévision (ex. « nous avons collecté »). Aucune preuve "
                        "n'a été fournie.")
                    break

    # P2 — le socle de l'agent 8 doit être repris, pas vidé.
    socle = {"approche": protocol.approche, "logique": protocol.logique,
             "type_recherche": protocol.type_recherche, "strategie": protocol.strategie}
    missing_socle = [k for k, v in socle.items() if not str(v or "").strip()]
    if missing_socle:
        violations.append(
            "P2 : le protocole ne reprend pas le socle vérifié de l'étape 8 (manquant : "
            + ", ".join(missing_socle) + "). Les choix de l'étape 8 ne se re-tranchent pas.")

    # P3 — taille d'échantillon chiffrée sans justification.
    ech = protocol.echantillonnage
    chiffre = ech.taille is not None or bool(re.search(r"\d", ech.taille_texte or ""))
    if chiffre and ech.type != EchantillonnageType.sans_objet:
        if not str(ech.justification or "").strip():
            violations.append(
                "P3 : une taille d'échantillon est avancée sans justification. Indiquez la base "
                "(contrainte, règle de détermination) ou laissez-la « à déterminer ».")
        elif ech.source_taille == SourceTaille.a_determiner:
            violations.append(
                "P3 : la taille est chiffrée mais sa source n'est pas établie (fournie, documentée "
                "ou à déterminer).")

    # P4 — techniques de terrain sans socle correspondant dans le diagnostic.
    categories = request.diagnostic_categories()
    collecte_diag = " ".join(
        str((c or {}).get("code", "")) + " " + str((c or {}).get("proposition", ""))
        for c in (categories.get("collecte") or []) if isinstance(c, dict))
    technique_names = " ".join(str(t.nom or "") for t in (protocol.techniques or []))
    terrain_used = [t for t in _TERRAIN_TECHNIQUES if t in _squash(technique_names)]
    if terrain_used and not collecte_diag.strip():
        violations.append(
            "P4 : le protocole prévoit une collecte de terrain ("
            + ", ".join(terrain_used) + ") alors que le diagnostic de l'étape 8 ne retient aucune "
            "technique de collecte. Signalez la contradiction ou revenez au socle vérifié.")

    # P5 — hypothèses ajoutées alors que l'étape 7 a conclu qu'elles ne sont pas pertinentes.
    if request.hypotheses_not_required() and re.search(r"\bhypoth[eè]se", text):
        violations.append(
            "P5 : des hypothèses apparaissent alors que l'étape 7 a conclu qu'elles ne sont PAS "
            "pertinentes pour ce travail. Ne pas en imposer.")

    # P6 — analyse inférentielle sur des données non quantitatives.
    approche = _squash(protocol.approche)
    qualitative = bool(re.search(r"qualitat", approche)) or "entretien" in _squash(technique_names)
    if qualitative and not re.search(r"quantitat|mixte", approche + " " + _squash(protocol.type_recherche)):
        used = [t for t in _INFERENTIAL if t in text]
        if used:
            violations.append(
                "P6 : une analyse inférentielle (" + ", ".join(used) + ") est proposée alors que "
                "le protocole est qualitatif. Vérifiez la compatibilité ou changez d'approche.")

    # P7 — causalité affirmée sans dispositif adéquat.
    dispositif = _squash(protocol.type_recherche + " " + protocol.strategie + " " + protocol.approche)
    experimental = bool(re.search(r"exp[ée]rimental|quasi[- ]exp|essai|contrôle", dispositif))
    if not experimental:
        for pattern in _CAUSALITY:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not _negation_near(text, match):
                violations.append(
                    "P7 : le document affirme une relation causale (« "
                    + match.group(0) + " ») alors que le dispositif ne le permet pas. Préférez une "
                    "association, ou écarter explicitement la causalité.")
                break

    # P8 — exigence d'établissement inventée (aucune consigne fournie).
    consignes = (request.university_instructions or "").strip()
    if not consignes:
        for pattern in _INSTITUTION:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                violations.append(
                    "P8 : le document présente « " + match.group(0) + " » comme une règle de "
                    "l'établissement alors qu'aucune consigne n'a été fournie. Indiquez qu'il "
                    "s'agit d'un usage courant, ou demandez les consignes.")
                break

    # P9 — contradiction connue non déclarée.
    if analysis.contradictions and not protocol.contradictions_diagnostic:
        violations.append(
            "P9 : des contradictions ont été relevées à l'étape d'analyse mais le protocole n'en "
            "déclare aucune. Elles doivent être reprises explicitement (jamais corrigées en silence).")

    return violations
