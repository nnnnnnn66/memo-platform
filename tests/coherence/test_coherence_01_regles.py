"""Faits transversaux X1–X12 : chacun éprouvé dans les DEUX sens."""

from coherence_helpers import (
    HYPOTHESE,
    dossier_complet,
    dossier_fusionne,
    dossier_hypothese_contredite,
    dossier_incomplet,
    dossier_normatif_non_examinable,
    dossier_non_verifie,
    dossier_objectif_non_couvert,
    dossier_reference_orpheline,
)

from research_coherence_verifier.analysis import coherence_rules, fusion
from research_coherence_verifier.schemas.input import CoherenceRequest


def _faits(payload):
    request = CoherenceRequest(**payload)
    dossier, constats = coherence_rules.run_facts(request)
    return dossier, constats


def _codes(constats):
    return {c.code for c in constats}


def _constat(constats, code):
    return next((c for c in constats if c.code == code), None)


# --- dossier sain : aucun fait ne doit être fabriqué -------------------------------------------

def test_dossier_coherent_ne_produit_aucun_fait():
    """Un dossier qui tient ne doit produire AUCUN constat : pas de faux positif."""
    _, constats = _faits(dossier_complet())
    assert constats == [], [c.constat for c in constats]


# --- X1 : étape transmise mais non vérifiée ----------------------------------------------------

def test_x1_etape_non_verifiee_signalee():
    _, constats = _faits(dossier_non_verifie())
    assert "X1" in _codes(constats)
    assert "objectifs" in " ".join(_constat(constats, "X1").elements)


def test_x1_absent_quand_tout_est_verifie():
    _, constats = _faits(dossier_complet())
    assert "X1" not in _codes(constats)


# --- X2 : socle absent -------------------------------------------------------------------------

def test_x2_question_absente_bloque():
    payload = dossier_complet()
    payload["upstream_question"] = None
    payload["upstream_results"] = {k: v for k, v in payload["upstream_results"].items()
                                   if k != "main_research_question"}
    _, constats = _faits(payload)
    constat = _constat(constats, "X2")
    assert constat is not None and constat.severite.value == "bloqueur"


def test_x2_absent_quand_le_socle_est_la():
    _, constats = _faits(dossier_complet())
    assert "X2" not in _codes(constats)


# --- X3 : fusion sujet / problème / problématique ----------------------------------------------

def test_x3_fusion_sujet_probleme_problematique_detectee():
    _, constats = _faits(dossier_fusionne())
    constat = _constat(constats, "X3")
    assert constat is not None, "la fusion doit être détectée"
    assert constat.severite.value == "bloqueur"
    assert constat.preuve                      # preuve obligatoire


def test_x3_absent_quand_les_textes_sont_distincts():
    _, constats = _faits(dossier_complet())
    assert "X3" not in _codes(constats)


def test_fusion_reconnait_la_recopie_et_distingue_les_themes():
    assert fusion.sont_fusionnes("Le télétravail et la productivité des développeurs d'Abidjan",
                                 "Le télétravail et la productivité des développeurs d'Abidjan")
    assert not fusion.sont_fusionnes(
        "Le télétravail et la productivité des développeurs d'Abidjan",
        "Les stratégies de fidélisation des clients bancaires au Sénégal")
    assert not fusion.sont_fusionnes("", "un texte quelconque")


# --- X4 / X5 : objectifs -------------------------------------------------------------------------

def test_x4_objectifs_absents():
    payload = dossier_complet()
    payload["upstream_objectives"] = {"general_objective": "", "specific_objectives": [],
                                     "verification_result": {"verified": True}}
    _, constats = _faits(payload)
    assert "X4" in _codes(constats)


def test_x5_objectifs_sans_rapport_avec_la_question():
    payload = dossier_complet()
    payload["upstream_objectives"] = {
        "general_objective": "Analyser la fidélisation des clients bancaires au Sénégal.",
        "specific_objectives": ["Identifier les leviers de rétention bancaire."],
        "verification_result": {"verified": True}}
    _, constats = _faits(payload)
    assert "X5" in _codes(constats)


def test_x5_absent_quand_les_objectifs_servent_la_question():
    _, constats = _faits(dossier_complet())
    assert "X5" not in _codes(constats)


# --- X6 : hypothèses vs décision de l'étape 7 ----------------------------------------------------

def test_x6_hypotheses_presentes_alors_que_jugees_inutiles():
    payload = dossier_complet()
    payload["upstream_hypotheses"] = {
        "hypotheses_decision": "HYPOTHESES_NOT_REQUIRED",
        "research_hypotheses": [{"id": "H1", "formulation": HYPOTHESE}],
        "verification_result": {"verified": True}}
    _, constats = _faits(payload)
    assert "X6" in _codes(constats)


def test_x6_hypotheses_requises_mais_absentes():
    payload = dossier_complet()
    payload["upstream_hypotheses"] = {"hypotheses_decision": "HYPOTHESES_RECOMMENDED",
                                      "research_hypotheses": [],
                                      "verification_result": {"verified": True}}
    _, constats = _faits(payload)
    assert "X6" in _codes(constats)


# --- X7 : examinabilité par la méthodologie ------------------------------------------------------

def test_x7_hypothese_relationnelle_face_a_une_methodologie_qualitative():
    _, constats = _faits(dossier_normatif_non_examinable())
    constat = _constat(constats, "X7")
    assert constat is not None
    assert constat.severite.value == "majeur"
    assert "hypotheses" in constat.elements and "methodologie" in constat.elements


def test_x7_absent_quand_le_dispositif_permet_l_inference():
    _, constats = _faits(dossier_complet())
    assert "X7" not in _codes(constats)


# --- X8 : objectifs non couverts -----------------------------------------------------------------

def test_x8_objectif_non_couvert():
    _, constats = _faits(dossier_objectif_non_couvert())
    assert "X8" in _codes(constats)


def test_x8_absent_quand_tout_est_couvert():
    _, constats = _faits(dossier_complet())
    assert "X8" not in _codes(constats)


# --- X9 : références orphelines ------------------------------------------------------------------

def test_x9_reference_orpheline_bloquante():
    _, constats = _faits(dossier_reference_orpheline())
    constat = _constat(constats, "X9")
    assert constat is not None and constat.severite.value == "bloqueur"
    assert "R99" in constat.preuve


def test_x9_absent_quand_les_references_existent():
    _, constats = _faits(dossier_complet())
    assert "X9" not in _codes(constats)


# --- X10 : résultats ignorés ---------------------------------------------------------------------

def test_x10_resultats_peu_repris():
    payload = dossier_complet()
    resultats = payload["upstream_results"]["computed_results"]["resultats"]
    payload["upstream_results"] = {
        **payload["upstream_results"],
        "computed_results": {"resultats": resultats + [
            {"id": f"R{i}", "libelle": f"mesure {i}", "valeur": str(i), "unite": ""}
            for i in range(4, 40)]}}
    payload["upstream_conclusion"] = {**payload["upstream_conclusion"],
                                      "references_resultats": ["R1"]}
    _, constats = _faits(payload)
    assert "X10" in _codes(constats)


# --- X11 : contradiction de statut d'hypothèse ---------------------------------------------------

def test_x11_statut_d_hypothese_contredit():
    _, constats = _faits(dossier_hypothese_contredite())
    constat = _constat(constats, "X11")
    assert constat is not None and constat.severite.value == "majeur"
    assert "non_examinable" in constat.preuve


def test_x11_absent_quand_les_statuts_concordent():
    _, constats = _faits(dossier_complet())
    assert "X11" not in _codes(constats)


# --- X12 : étape vérifiée au contenu vide --------------------------------------------------------

def test_x12_etape_verifiee_sans_contenu():
    payload = dossier_complet()
    payload["upstream_methodology"] = {"protocol": {}, "verification_result": {"verified": True}}
    payload["upstream_results"] = {"computed_results": {"resultats": []},
                                   "plan": {"objectifs_non_couverts": []},
                                   "verification_result": {"verified": True}}
    _, constats = _faits(payload)
    assert "X12" in _codes(constats)


def test_x12_absent_quand_les_etapes_sont_renseignees():
    _, constats = _faits(dossier_complet())
    assert "X12" not in _codes(constats)


# --- preuve obligatoire partout ------------------------------------------------------------------

def test_tout_constat_porte_une_preuve():
    for payload in (dossier_fusionne(), dossier_objectif_non_couvert(),
                    dossier_reference_orpheline(), dossier_hypothese_contredite(),
                    dossier_normatif_non_examinable(), dossier_incomplet()):
        _, constats = _faits(payload)
        for constat in constats:
            assert str(constat.preuve).strip(), f"constat sans preuve : {constat.code}"
            assert str(constat.recommandation).strip(), f"constat sans recommandation : {constat.code}"


def test_etat_du_dossier_recense_presence_et_verification():
    dossier, _ = _faits(dossier_incomplet())
    assert len(dossier.etapes_presentes) == 2
    assert len(dossier.etapes_absentes) == 9
    assert dossier.exploitable
