"""Les FAITS transversaux X1–X12, établis par le PROGRAMME (SPEC §9 étape 2).

Principe : tout ce qui est confrontable mécaniquement est calculé ici, sans solliciter de modèle. Ces
faits sont fournis à l'audit sémantique (P1), qui peut les CONFIRMER, les NUANCER ou les INFIRMER en le
motivant — mais jamais les supprimer en silence (contrôle C4 du contrôleur de l'audit).

Chaque constat porte une PREUVE : c'est la règle dure de cet agent.
"""

from ..schemas.audit import Axe, DossierState, Finding, Origine, Severite
from ..schemas.input import ETAPES, CoherenceRequest
from . import fusion

#: Marqueurs d'une hypothèse de RELATION (à examiner par inférence, pas seulement par description).
_RELATION = ["associ", "relation", "corrél", "correl", "lien ", "influenc", "impact", "effet",
             "augment", "diminu", "différ", "compar", "plus que", "moins que", "détermin",
             "explique", "varie"]
#: Marqueurs d'un dispositif capable d'INFÉRENCE.
_INFERENCE = ["quantitativ", "test ", "test d", "corrél", "correl", "régression", "regression",
              "khi", "chi2", "khi-deux", "anova", "t de student", "moyenne", "coefficient",
              "significativ", "échantillon représentatif", "comparaison de moyennes"]
#: Ordre de grandeur d'un effectif suffisant pour une analyse relationnelle.
_EFFECTIF_MIN = 30


def etat_du_dossier(request: CoherenceRequest) -> DossierState:
    presentes, verifiees, non_verifiees, absentes = [], [], [], []
    for numero, nom in ETAPES.items():
        payload = request.payloads().get(numero)
        libelle = f"{numero} {nom}"
        if payload is None:
            absentes.append(libelle)
            continue
        presentes.append(libelle)
        (verifiees if payload.is_verified else non_verifiees).append(libelle)

    service = {
        "sujet": request.effective_subject(),
        "problème de recherche": request.effective_problem(),
        "problématique": request.effective_problematic(),
        "question de recherche": request.effective_question(),
        "objectif général": request.effective_general_objective(),
        "objectifs spécifiques": request.effective_specific_objectives(),
        "hypothèses": request.effective_hypotheses(),
        "méthodologie": request.methodology_protocol(),
        "résultats calculés": request.upstream_results.computed_ids()
        if request.upstream_results else set(),
        "conclusion": request.upstream_conclusion.reponse_question()
        if request.upstream_conclusion else "",
    }
    presents = [nom for nom, valeur in service.items() if valeur]
    absents = [nom for nom, valeur in service.items() if not valeur]
    return DossierState(
        etapes_presentes=presentes, etapes_verifiees=verifiees,
        etapes_non_verifiees=non_verifiees, etapes_absentes=absentes,
        elements_de_service=presents, elements_de_service_absents=absents,
        exploitable=len(presentes) >= 2,
    )


def _f(code, axe, severite, elements, constat, preuve, recommandation) -> Finding:
    return Finding(code=code, axe=axe, severite=severite, elements=list(elements),
                   constat=constat, preuve=preuve, recommandation=recommandation,
                   origine=Origine.deterministe)


#: Clés de métadonnées qui ne constituent PAS un contenu (statuts, verdicts, traces).
_META = {
    "agent", "version", "status", "document_status", "generated_at", "research_id", "session_id",
    "provenance", "validation", "verification_result", "student_validation", "confidence", "evidence",
    "limits_of_this_output", "coherence_controls", "unknowns", "missing_information",
    "informations_a_confirmer", "questions_for_human", "lacunes_et_incertitudes",
}

#: Longueur minimale d'une chaîne pour compter comme un contenu (évite les libellés).
_LONGUEUR_MINIMALE = 12


def _substantiel(valeur) -> bool:
    if isinstance(valeur, str):
        return len(valeur.strip()) >= _LONGUEUR_MINIMALE
    if isinstance(valeur, dict):
        return any(_substantiel(v) for cle, v in valeur.items() if cle not in _META)
    if isinstance(valeur, (list, tuple, set)):
        return any(_substantiel(v) for v in valeur)
    return False


def _a_du_contenu(payload) -> bool:
    """Vrai si la sortie porte un contenu substantiel, QUELLE QUE SOIT LA CLÉ employée.

    Un contrôle fondé sur une liste de champs attendus produit des faux positifs dès qu'une étape
    nomme autrement son contenu (cas réel : l'étape 3 place sa revue dans `synthesis`).
    """
    return any(_substantiel(valeur) for cle, valeur in payload.model_dump().items()
               if cle not in _META)


def run_facts(request: CoherenceRequest) -> tuple[DossierState, list[Finding]]:
    dossier = etat_du_dossier(request)
    constats: list[Finding] = []

    # X1 — une étape transmise mais NON vérifiée : l'audit porterait sur un brouillon.
    if dossier.etapes_non_verifiees:
        constats.append(_f(
            "X1", Axe.completude,
            Severite.bloqueur if len(dossier.etapes_non_verifiees) > 2 else Severite.majeur,
            dossier.etapes_non_verifiees,
            f"{len(dossier.etapes_non_verifiees)} étape(s) transmise(s) sans vérification réussie.",
            "statut de vérification : " + ", ".join(dossier.etapes_non_verifiees),
            "Finaliser la vérification des étapes concernées, ou présenter explicitement l'audit comme "
            "portant sur des brouillons."))

    # X2 — socle absent : sans sujet ni question, rien ne peut être confronté.
    manquants = [nom for nom in ("sujet", "question de recherche")
                 if nom in dossier.elements_de_service_absents]
    if manquants:
        constats.append(_f(
            "X2", Axe.completude, Severite.bloqueur, manquants,
            f"Élément(s) de service absent(s) du dossier : {', '.join(manquants)}.",
            "aucune valeur exploitable trouvée dans les sorties amont",
            "Transmettre le sujet exact et la question de recherche validée : sans eux, aucune "
            "confrontation transversale n'est possible."))

    # X3 — fusion sujet / problème / problématique.
    sujet, probleme, problematique = (request.effective_subject(), request.effective_problem(),
                                      request.effective_problematic())
    libelles = {"sujet": "le sujet", "problème": "le problème", "problématique": "la problématique"}
    paires = [("sujet", sujet, "problème", probleme), ("sujet", sujet, "problématique", problematique),
              ("problème", probleme, "problématique", problematique)]
    for gauche, texte_g, droite, texte_d in paires:
        if fusion.sont_fusionnes(texte_g, texte_d):
            constats.append(_f(
                "X3", Axe.fusion, Severite.bloqueur, [gauche, droite],
                f"{libelles[gauche].capitalize()} et {libelles[droite]} sont le MÊME texte : ces "
                "niveaux ne peuvent pas être fusionnés.",
                fusion.indice(texte_g, texte_d),
                f"Redistinguer {libelles[gauche]} et {libelles[droite]} : le sujet délimite l'objet, "
                "le problème énonce la difficulté, la problématique construit la question."))

    # X4 — aucun objectif identifiable.
    if not request.effective_general_objective() and not request.effective_specific_objectives():
        constats.append(_f(
            "X4", Axe.service, Severite.majeur, ["objectifs"],
            "Aucun objectif (général ou spécifique) n'est identifiable : rien ne décline la question.",
            "objectif général et objectifs spécifiques vides dans le dossier",
            "Formuler l'objectif général puis les objectifs spécifiques."))

    # X5 — les objectifs ne servent pas la question (recouvrement lexical nul).
    question = request.effective_question()
    objectifs = ([request.effective_general_objective()]
                 + list(request.effective_specific_objectives()))
    if question and any(objectifs):
        joint = " ".join(objectifs)
        if fusion.recouvrement(question, joint) == 0.0:
            constats.append(_f(
                "X5", Axe.service, Severite.majeur, ["question", "objectifs"],
                "Aucun terme significatif n'est commun à la question et aux objectifs : les objectifs "
                "semblent servir un autre objet.",
                fusion.indice(question, joint),
                "Réécrire les objectifs en fonction de la question de recherche."))

    # X6 — hypothèses et décision de l'étape 7 incohérentes.
    hypotheses = request.effective_hypotheses()
    if hypotheses and not request.hypotheses_requises():
        decision = "non transmise"
        payload = request.upstream_hypotheses
        if payload is not None:
            decision = str(payload.hypotheses_decision or "non transmise")
        if decision != "non transmise":
            constats.append(_f(
                "X6", Axe.contradiction, Severite.majeur, ["hypotheses"],
                f"Des hypothèses sont présentes alors que l'étape 7 a décidé « {decision} ».",
                f"{len(hypotheses)} hypothèse(s) transmise(s) contre décision « {decision} »",
                "Trancher : soit les hypothèses sont retirées, soit la décision de l'étape 7 est "
                "révisée."))
    if request.hypotheses_requises() and not hypotheses:
        constats.append(_f(
            "X6", Axe.contradiction, Severite.majeur, ["hypotheses"],
            "L'étape 7 a jugé des hypothèses nécessaires, mais aucune hypothèse n'est présente.",
            "décision de l'étape 7 : hypothèses recommandées ; liste transmise vide",
            "Transmettre les hypothèses validées, ou réviser la décision de l'étape 7."))

    # X7 — hypothèses d'EXAMINABILITÉ : une relation ne s'examine pas par une description.
    methode = fusion.normaliser(request.methodology_text())
    relationnelles = [h for h in hypotheses
                      if any(m in fusion.normaliser(h) for m in _RELATION)]
    capable = any(m in methode for m in _INFERENCE)
    if relationnelles and methode and not capable:
        constats.append(_f(
            "X7", Axe.examinabilite, Severite.majeur, ["hypotheses", "methodologie"],
            f"{len(relationnelles)} hypothèse(s) énoncent une relation, mais le dispositif décrit ne "
            "comporte aucun moyen d'inférence : ces hypothèses ne sont pas examinables en l'état.",
            "hypothèse : « " + relationnelles[0][:110] + " » ; dispositif : "
            + (request.methodology_text()[:110] or "non décrit"),
            "Soit ajouter au protocole un dispositif capable de traiter la relation (mesure, "
            "comparaison, test), soit reformuler les hypothèses en questions descriptives."))

    # X8 — objectifs non couverts par les résultats.
    if request.upstream_results is not None:
        non_couverts = request.upstream_results.objectifs_non_couverts()
        if non_couverts:
            constats.append(_f(
                "X8", Axe.couverture, Severite.majeur, ["objectifs", "resultats"],
                f"{len(non_couverts)} objectif(s) ne sont couverts par aucun résultat.",
                "objectifs déclarés non couverts à l'étape 10 : "
                + " | ".join(o[:90] for o in non_couverts[:4]),
                "Soit produire les résultats manquants, soit déclarer l'objectif non traité dans la "
                "conclusion et en expliquer la raison."))

    # X9 — références ORPHELINES : la conclusion cite un résultat qui n'existe pas.
    if request.upstream_conclusion is not None and request.upstream_results is not None:
        ids = request.upstream_results.computed_ids()
        citees = [str(r).strip() for r in request.upstream_conclusion.references_resultats
                  if str(r).strip()]
        orphelines = [r for r in citees if r not in ids]
        if orphelines and ids:
            constats.append(_f(
                "X9", Axe.tracabilite, Severite.bloqueur, ["resultats", "conclusion"],
                "La conclusion cite des résultats qui n'existent pas dans l'étape 10.",
                "références citées absentes des résultats calculés : " + ", ".join(orphelines[:6]),
                "Corriger les références de la conclusion (reprendre les identifiants réels), ou "
                "produire le résultat manquant dans l'étape 10."))

        # X10 — résultats IGNORÉS par la conclusion.
        if ids and citees:
            ratio = len(set(citees) & ids) / len(ids)
            if ratio < 0.20 and len(ids) >= 5:
                constats.append(_f(
                    "X10", Axe.fidelite, Severite.mineur, ["resultats", "conclusion"],
                    "La conclusion ne reprend qu'une très faible part des résultats disponible : "
                    "elle risque de ne pas rendre compte du travail réalisé.",
                    f"{len(set(citees) & ids)} résultat(s) repris sur {len(ids)} calculés "
                    f"({ratio:.0%})",
                    "Vérifier que les résultats essentiels sont bien synthétisés, ou expliquer "
                    "pourquoi certains sont écartés."))

        # X11 — contradiction de statut d'hypothèse entre l'étape 10 et la conclusion.
        etape10 = {fusion.normaliser(h.get("hypothese", "")): str(h.get("statut", "")).strip()
                   for h in request.upstream_results.hypotheses_examinees()}
        for bilan in request.upstream_conclusion.bilan_hypotheses():
            cle = fusion.normaliser(bilan.get("hypothese", ""))
            statut11 = str(bilan.get("statut", "")).strip()
            for formule, statut10 in etape10.items():
                if not cle or not statut10:
                    continue
                if cle in formule or formule in cle:
                    if statut10 == "non_examinable" and statut11 in ("soutenue", "non_soutenue"):
                        constats.append(_f(
                            "X11", Axe.contradiction, Severite.majeur, ["resultats", "conclusion"],
                            "Le statut d'une hypothèse change entre l'étape 10 et la conclusion.",
                            f"étape 10 : « {statut10} » ; conclusion : « {statut11} » — hypothèse : "
                            + str(bilan.get("hypothese", ""))[:90],
                            "Reprendre dans la conclusion le statut établi sur les résultats ; si les "
                            "données ne permettaient pas de trancher, la conclusion ne peut pas le "
                            "faire."))
                    break

    # X12 — une étape marquée VÉRIFIÉE au contenu vide.
    # Le contrôle est GÉNÉRIQUE (présence d'un contenu substantiel, quelle qu'en soit la clé) : lister
    # les champs attendus par étape produirait des faux positifs dès qu'une étape emploie d'autres clés
    # (défaut constaté sur l'étape 3, dont le contenu vit dans `synthesis`).
    vides: list[str] = []
    for numero, nom in ETAPES.items():
        payload = request.payloads().get(numero)
        if payload is None or not payload.is_verified:
            continue
        if not _a_du_contenu(payload):
            vides.append(f"{numero} {nom}")
    if vides:
        constats.append(_f(
            "X12", Axe.integrite, Severite.majeur, vides,
            "Des étapes sont marquées vérifiées alors que leur contenu principal est vide.",
            "étapes concernées : " + ", ".join(vides),
            "Reprendre les étapes concernées : un verdict de vérification sans contenu n'est pas "
            "exploitable."))

    return dossier, constats
