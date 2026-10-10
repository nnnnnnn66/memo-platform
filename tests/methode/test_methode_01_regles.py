"""Contrôles déterministes P1–P9 : le juge du fond est le vérificateur, pas ces règles.

Chaque contrôle est éprouvé dans les deux sens : il DOIT refuser ce qui est fautif et NE DOIT PAS
refuser ce qui est juste (leçon du projet : un contrôle mal calibré bloque une campagne saine).
"""

from methode_helpers import upstream_diagnostic

from methodology_agent.analysis import protocol_rules as rules
from methodology_agent.schemas.analysis import Analysis
from methodology_agent.schemas.draft import DraftSection, MethodologyDraft
from methodology_agent.schemas.matrix import CoherenceMatrix
from methodology_agent.schemas.protocol import (
    Echantillonnage,
    EchantillonnageType,
    Limite,
    MethodeAnalyse,
    Protocol,
    SourceTaille,
    StatutAffirmation,
    TechniqueCollecte,
)

SOCLE = {"approche": "quantitative", "logique": "hypothetico_deductive",
         "type_recherche": "explicative", "strategie": "enquete"}


def _protocol(**overrides):
    payload = dict(SOCLE)
    payload.update({
        "terrain": "Entreprises d'Abidjan",
        "techniques": [TechniqueCollecte(nom="questionnaire", role="mesurer la relation")],
        "analyses": [MethodeAnalyse(nom="statistiques descriptives", objet="décrire")],
        "echantillonnage": Echantillonnage(type=EchantillonnageType.non_probabiliste),
    })
    payload.update(overrides)
    return Protocol(**payload)


def _draft(*contenus, statut=StatutAffirmation.prevu):
    return MethodologyDraft(sections=[DraftSection(titre=f"Section {i}", contenu=c, statut=statut)
                                      for i, c in enumerate(contenus, 1)])


def _check(request, protocol=None, draft=None, analysis=None):
    return rules.run_checks(request, protocol or _protocol(), CoherenceMatrix(),
                            draft or _draft("Le protocole décrira la démarche prévue."),
                            analysis or Analysis())


def test_p1_collecte_au_passe_sans_preuve_refusee(request_factory):
    draft = _draft("Nous avons collecté 120 questionnaires auprès des développeurs.")
    violations = _check(request_factory(), draft=draft)
    assert any(v.startswith("P1") for v in violations)


def test_p1_passe_accepte_si_preuve_fournie(request_factory):
    """Une preuve fournie par l'étudiant lève le refus : le réalisé est autorisé, mais prouvé."""
    request = request_factory(realise_preuves=["Compte rendu de la pré-enquête (12 réponses)."])
    draft = _draft("Les entretiens exploratoires ont été réalisés auprès de six développeurs.",
                   statut=StatutAffirmation.realise)
    violations = _check(request, draft=draft)
    assert not any(v.startswith("P1") for v in violations)


def test_p1_phrase_qui_ecarte_le_passe_n_est_pas_refusee(request_factory):
    draft = _draft("Le protocole ne prévoit pas de collecte déjà effectuée : aucune donnée n'a été "
                   "recueillie à ce stade.")
    violations = _check(request_factory(), draft=draft)
    assert not any(v.startswith("P1") for v in violations)


def test_p2_socle_vide_refuse(request_factory):
    violations = _check(request_factory(), protocol=_protocol(approche=""))
    assert any(v.startswith("P2") for v in violations)


def test_p3_taille_sans_justification_refusee(request_factory):
    protocol = _protocol(echantillonnage=Echantillonnage(
        type=EchantillonnageType.non_probabiliste, taille=150))
    violations = _check(request_factory(), protocol=protocol)
    assert any(v.startswith("P3") for v in violations)


def test_p3_taille_justifiee_acceptee(request_factory):
    protocol = _protocol(echantillonnage=Echantillonnage(
        type=EchantillonnageType.non_probabiliste, taille=150,
        justification="Effectif total accessible (150) : recensement exhaustif.",
        source_taille=SourceTaille.documentee))
    violations = _check(request_factory(), protocol=protocol)
    assert not any(v.startswith("P3") for v in violations)


def test_p3_taille_absente_acceptee(request_factory):
    """Ne pas connaître la taille est légitime : c'est l'invention qui est refusée."""
    violations = _check(request_factory(), protocol=_protocol(
        echantillonnage=Echantillonnage(type=EchantillonnageType.non_probabiliste,
                                        taille_texte="à déterminer", source_taille=SourceTaille.a_determiner)))
    assert not any(v.startswith("P3") for v in violations)


def test_p4_terrain_sans_socle_refuse(request_factory):
    """Le diagnostic de l'étape 8 ne retient AUCUNE technique de collecte."""
    request = request_factory(
        upstream_methodology_diagnostic=upstream_diagnostic(collecte=[]))
    violations = _check(request)
    assert any(v.startswith("P4") for v in violations)


def test_p4_terrain_avec_socle_accepte(request_factory):
    violations = _check(request_factory())
    assert not any(v.startswith("P4") for v in violations)


def test_p5_hypotheses_alors_que_non_pertinentes(request_factory):
    request = request_factory(upstream_hypotheses={
        "agent": "research_hypotheses_agent", "status": "validated",
        "hypotheses_decision": "HYPOTHESES_NOT_REQUIRED", "research_hypotheses": [],
        "verification_result": {"verified": True, "verifier_status": "verified"}})
    draft = _draft("Nous examinerons l'hypothèse H1 selon laquelle la coordination est liée à la "
                   "productivité.")
    violations = _check(request, draft=draft)
    assert any(v.startswith("P5") for v in violations)


def test_p6_inferentiel_sur_qualitatif_refuse(request_factory):
    protocol = _protocol(
        approche="qualitative", type_recherche="comprehension",
        techniques=[TechniqueCollecte(nom="entretien semi-directif", role="comprendre")],
        analyses=[MethodeAnalyse(nom="test du khi-2", objet="comparer les groupes")])
    violations = _check(request_factory(), protocol=protocol)
    assert any(v.startswith("P6") for v in violations)


def test_p6_mixte_avec_inferentiel_accepte(request_factory):
    protocol = _protocol(
        approche="mixte", techniques=[TechniqueCollecte(nom="entretien", role="comprendre")],
        analyses=[MethodeAnalyse(nom="test du khi-2", objet="comparer")])
    violations = _check(request_factory(), protocol=protocol)
    assert not any(v.startswith("P6") for v in violations)


def test_p7_causalite_sans_dispositif_refusee(request_factory):
    draft = _draft("Le télétravail provoque une baisse de la productivité perçue.")
    violations = _check(request_factory(), draft=draft)
    assert any(v.startswith("P7") for v in violations)


def test_p7_causalite_ecartee_non_refusee(request_factory):
    """Une phrase qui ÉCARTE la causalité ne doit pas déclencher le contrôle (leçon M4)."""
    draft = _draft("Le dispositif ne permettra pas d'établir une causalité : aucune lecture "
                   "causale n'est proposée.")
    violations = _check(request_factory(), draft=draft)
    assert not any(v.startswith("P7") for v in violations)


def test_p7_causalite_avec_experimental_acceptee(request_factory):
    protocol = _protocol(type_recherche="expérimentale", strategie="essai contrôlé randomisé")
    draft = _draft("Le dispositif expérimental permettra d'établir que l'intensité du télétravail "
                   "provoque une variation de la productivité.")
    violations = _check(request_factory(), protocol=protocol, draft=draft)
    assert not any(v.startswith("P7") for v in violations)


def test_p8_exigence_d_etablissement_inventee(request_factory):
    draft = _draft("L'université exige un échantillon de cent répondants pour tout mémoire.")
    violations = _check(request_factory(), draft=draft)
    assert any(v.startswith("P8") for v in violations)


def test_p8_consignes_fournies_lever_le_refus(request_factory):
    request = request_factory(
        university_instructions="Le guide du mémoire impose un chapitre méthodologique de 15 pages.")
    draft = _draft("L'université exige une section méthodologique d'environ quinze pages.")
    violations = _check(request, draft=draft)
    assert not any(v.startswith("P8") for v in violations)


def test_p9_contradiction_non_declaree(request_factory):
    analysis = Analysis(contradictions=["stratégie expérimentale mais collecte documentaire"])
    violations = _check(request_factory(), analysis=analysis)
    assert any(v.startswith("P9") for v in violations)


def test_p9_contradiction_declaree_acceptee(request_factory):
    analysis = Analysis(contradictions=["stratégie expérimentale mais collecte documentaire"])
    protocol = _protocol(contradictions_diagnostic=["stratégie expérimentale / collecte "
                                                    "documentaire : arbitrage demandé"])
    violations = _check(request_factory(), protocol=protocol, analysis=analysis)
    assert not any(v.startswith("P9") for v in violations)


def test_limites_et_instruments_sont_des_modeles(request_factory):
    protocol = _protocol(limites=[Limite(description="échantillon non probabiliste",
                                         consequence="pas de généralisation")])
    violations = _check(request_factory(), protocol=protocol)
    assert not any(v.startswith("P1") for v in violations)
