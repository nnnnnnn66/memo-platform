"""Routage d'une question libre de l'étudiant vers l'étape (donc l'agent) qui la porte.

L'étudiant écrit une phrase ; l'orchestrateur **désigne** l'étape responsable et **le dit**. C'est
le rôle que l'orchestrateur tient déjà pour les passations : seul intermédiaire, les agents ne se
parlent jamais et l'étudiant ne les connaît pas.

CE MODULE N'APPELLE AUCUN MODÈLE DE LANGAGE — propriété documentée de l'orchestrateur, et choix
délibéré ici :
- budget 0 € : le quota de l'étudiant reste réservé à la production de son mémoire ;
- **explicabilité** : on peut montrer à l'étudiant POURQUOI sa question a été rattachée à cette
  étape (les mots reconnus), ce qu'un modèle ne permet pas ;
- **sécurité (OWASP LLM01)** : le texte de l'étudiant n'est jamais interprété comme une instruction
  — il est seulement comparé à un vocabulaire fermé. Une injection n'a rien à injecter.

Le texte est normalisé (minuscules, sans accents, ponctuation réduite à des espaces) : c'est
pourquoi le vocabulaire ci-dessous est écrit SANS ACCENT. Ne pas les « corriger ».
"""

import unicodedata

# Le vocabulaire de chaque étape : des expressions (qui lèvent l'ambiguïté, elles pèsent lourd) et
# des mots (plus faibles, mais qui rattrapent une question courte).
#
# Les conflits connus sont tranchés explicitement :
# - « question » seul ne renvoie PAS à l'étape 5 (l'étudiant dit « j'ai une question ») : il faut
#   l'expression « question de recherche ».
# - « methode » / « methodologie » → étape 9 ; « approche » / « demarche » / « qualitatif » →
#   étape 8. Un étudiant qui demande « ma méthodologie est-elle bonne ? » parle de l'étape 9.
# - « memoire » n'est volontairement PAS un mot-clé : c'est le mot le plus employé par l'étudiant,
#   il ne désigne aucune étape.
# - « donnees » seul est ambigu (on les collecte en 9, on les analyse en 10) : seules les
#   expressions le rattachent.
VOCABULAIRE: dict[int, dict[str, tuple[str, ...]]] = {
    1: {
        "phrases": ("mon sujet", "sujet de memoire", "sujet du memoire", "mon theme",
                    "reformuler mon sujet", "changer de sujet", "titre du memoire",
                    "choix du sujet", "sujet de recherche"),
        "mots": ("sujet", "intitule", "filiere", "specialite", "domaine"),
    },
    2: {
        "phrases": ("probleme de recherche", "mon probleme", "probleme de depart",
                    "constat de depart", "quel probleme", "probleme concret", "probleme social"),
        "mots": ("probleme", "difficulte", "dysfonctionnement", "constat", "ecart", "lacune",
                 "insuffisance", "anomalie"),
    },
    3: {
        "phrases": ("revue de litterature", "revue de la litterature", "etat de l'art",
                    "etat des connaissances", "cadre theorique", "recherche documentaire",
                    "les sources", "les auteurs", "les articles"),
        "mots": ("litterature", "bibliographie", "article", "auteur", "source", "citation",
                 "reference", "theorie", "theorique", "ouvrage", "publication", "lecture",
                 "documentaire"),
    },
    4: {
        "phrases": ("problematique", "ma problematique", "angle de recherche",
                    "positionnement de la recherche", "cadrage de l'etude",
                    "pertinence de l'etude"),
        "mots": ("problematique", "cadrage", "posture", "positionnement", "pertinence"),
    },
    5: {
        "phrases": ("question de recherche", "questions de recherche",
                    "ma question de recherche", "formuler ma question"),
        "mots": ("interrogation", "questionnement"),
    },
    6: {
        "phrases": ("objectif general", "objectifs specifiques", "objectif de recherche",
                    "but de la recherche", "mes objectifs", "quel objectif"),
        "mots": ("objectif", "but", "visee", "cible", "finalite", "attendu"),
    },
    7: {
        "phrases": ("hypothese de recherche", "mes hypotheses", "hypotheses de travail",
                    "formuler une hypothese"),
        "mots": ("hypothese", "conjecture", "supposition", "presomption", "postulat"),
    },
    8: {
        "phrases": ("orientation methodologique", "approche methodologique", "quelle methode",
                    "choix methodologique", "approche qualitative", "approche quantitative",
                    "ma demarche", "posture epistemologique"),
        "mots": ("qualitatif", "quantitatif", "qualitative", "quantitative", "deductif",
                 "inductif", "exploratoire", "descriptif", "explicatif", "epistemologie",
                 "approche", "demarche"),
    },
    9: {
        "phrases": ("protocole de recherche", "collecte des donnees", "collecte de donnees",
                    "echantillon", "echantillonnage", "terrain d'etude", "guide d'entretien",
                    "outil de collecte", "population d'etude", "ma methodologie", "ma methode"),
        "mots": ("methode", "methodologie", "protocole", "terrain", "enquete", "entretien",
                 "questionnaire", "sondage", "observation", "variable", "collecte",
                 "instrument", "population", "mesure"),
    },
    10: {
        "phrases": ("analyse des donnees", "analyse des resultats", "traitement des donnees",
                    "resultats obtenus", "mes resultats", "interpretation des resultats"),
        "mots": ("resultat", "analyse", "chiffre", "statistique", "tableau", "graphique",
                 "interpretation", "codage", "occurrence", "frequence"),
    },
    13: {
        "phrases": ("coherence", "verification globale", "mon dossier est-il coherent",
                    "tout est-il coherent", "verifier la coherence", "l'ensemble est-il coherent"),
        "mots": ("coherence", "coherent", "incoherence", "incoherent", "contradiction",
                 "alignement"),
    },
    11: {
        "phrases": ("conclusion", "ma conclusion", "synthese finale", "reponse a ma question",
                    "apports de la recherche", "limites de la recherche",
                    "perspectives de recherche", "ouverture"),
        "mots": ("conclusion", "conclure", "synthese", "apport", "ouverture", "perspective",
                 "recommandation"),
    },
}

POIDS_PHRASE = 10
POIDS_MOT = 3
LONGUEUR_MINIMALE = 3
LONGUEUR_MAXIMALE = 1000
# En dessous de cette longueur, un mot ne rattrape pas ses variantes par préfixe : « but »
# matcherait n'importe quoi.
LONGUEUR_MOT_VARIANTE = 5
# Une étape secondaire n'est retenue que si elle atteint cette part du meilleur score : sans cela,
# un mot commun (« analyse ») ferait apparaître tout le parcours.
SEUIL_RETENUE = 0.6
CONFIANCE_HAUTE = 10
CONFIANCE_MOYENNE = 6


def normaliser(texte: str) -> str:
    """Minuscules, sans accents, ponctuation réduite à des espaces.

    `échantillon` → `echantillon`, `l'état de l'art` → `l etat de l art`. C'est ce qui permet de
    comparer un vocabulaire écrit sans accent à ce qu'un étudiant tape vraiment.
    """
    decompose = unicodedata.normalize("NFKD", str(texte or "").lower())
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    propre = "".join(c if (c.isalnum() or c.isspace()) else " " for c in sans_accents)
    return " ".join(propre.split())


def _jetons(texte_normalise: str) -> set[str]:
    return set(texte_normalise.split())


# Le vocabulaire est normalisé UNE FOIS, au chargement : on peut donc l'écrire lisiblement
# (« état de l'art », « guide d'entretien ») sans qu'une apostrophe ou un accent fasse échouer un
# rattachement. Défaut trouvé par les tests : « l'état de l'art » ne trouvait pas « etat de l'art »,
# parce que la normalisation ne s'appliquait qu'à la question.
VOCABULAIRE_NORMALISE: dict[int, dict[str, tuple[str, ...]]] = {
    numero: {"phrases": tuple(normaliser(item) for item in vocabulaire["phrases"]),
             "mots": tuple(normaliser(item) for item in vocabulaire["mots"])}
    for numero, vocabulaire in VOCABULAIRE.items()}


def _marquer(texte: str, jetons: set[str], vocabulaire: dict) -> tuple[int, list[str]]:
    """Le score d'une étape et les indices qui l'ont produit (expressions puis mots)."""
    score = 0
    indices: list[str] = []
    for expression in vocabulaire["phrases"]:
        if expression in texte:
            score += POIDS_PHRASE
            indices.append(expression)
    for mot in vocabulaire["mots"]:
        reconnu = any(jeton == mot or (len(mot) >= LONGUEUR_MOT_VARIANTE and jeton.startswith(mot))
                      for jeton in jetons)
        if reconnu:
            score += POIDS_MOT
            indices.append(mot)
    return score, indices


def router(question: str) -> dict:
    """Désigne l'étape responsable d'une question — ou dit honnêtement qu'il n'a pas su.

    Renvoie `principale: None` quand rien ne correspond : l'orchestrateur ne devine JAMAIS. Une
    question non rattachée se voit répondre qu'elle n'a pas été rattachée et qu'il faut la
    préciser.
    """
    texte = normaliser(question)
    if len(texte) < LONGUEUR_MINIMALE:
        return {"principale": None, "etapes": [], "indices": [], "scores": {},
                "confiance": "aucune", "methode": "mots-cles"}

    jetons = _jetons(texte)
    scores: dict[int, int] = {}
    indices_par_etape: dict[int, list[str]] = {}
    for numero, vocabulaire in VOCABULAIRE_NORMALISE.items():
        score, indices = _marquer(texte, jetons, vocabulaire)
        if score:
            scores[numero] = score
            indices_par_etape[numero] = indices

    if not scores:
        return {"principale": None, "etapes": [], "indices": [], "scores": {},
                "confiance": "aucune", "methode": "mots-cles"}

    # Tri : meilleur score d'abord ; à égalité, l'étape la plus avancée dans le parcours (elle est
    # plus spécifique que les premières, dont les mots sont très génériques).
    classement = sorted(scores.items(), key=lambda item: (-item[1], -item[0]))
    principale, meilleur = classement[0]
    seuil = max(POIDS_MOT, meilleur * SEUIL_RETENUE)
    retenues = [numero for numero, score in classement if score >= seuil]

    if meilleur >= CONFIANCE_HAUTE:
        confiance = "haute"
    elif meilleur >= CONFIANCE_MOYENNE:
        confiance = "moyenne"
    else:
        confiance = "faible"

    # Deux étapes à égalité parfaite en tête : le choix n'est pas tranché, on le dit. C'est le cas
    # typique de « mes hypothèses et ma méthodologie sont-elles cohérentes ? ».
    if len(classement) > 1 and classement[1][1] == meilleur:
        confiance = "faible"

    return {
        "principale": principale,
        "etapes": retenues,
        "indices": indices_par_etape[principale],
        "scores": dict(classement),
        "confiance": confiance,
        "methode": "mots-cles",
    }
