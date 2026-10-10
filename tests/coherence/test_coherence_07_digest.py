"""Le digest envoyé au modèle ne peut pas dénaturer le dossier (défaut réel corrigé).

Défaut constaté sur la campagne réelle : un digest qui coupait la liste des résultats (60 premiers) et
celle des références (40 premières) a fait conclure à l'audit que la conclusion citait des résultats
« absents » — alors que l'étape 10 en comptait 106 et que ZÉRO référence n'était orpheline. Le modèle
ne doit jamais voir une liste tronquée sans que la coupe soit visible.
"""

from coherence_helpers import dossier_complet

from research_coherence_verifier.pipeline import security_layer
from research_coherence_verifier.schemas.input import CoherenceRequest


def _request_avec_resultats(nb: int):
    payload = dossier_complet()
    resultats = [{"id": f"R{i}", "libelle": f"mesure numéro {i} du corpus analysé", "valeur":
                  str(i), "unite": ""} for i in range(1, nb + 1)]
    payload["upstream_results"] = {
        **payload["upstream_results"],
        "computed_results": {"resultats": resultats}}
    payload["upstream_conclusion"] = {
        **payload["upstream_conclusion"],
        "references_resultats": [f"R{i}" for i in range(1, nb + 1)]}
    return CoherenceRequest(**payload)


def test_tous_les_identifiants_de_l_etape_10_sont_dans_le_digest():
    request = _request_avec_resultats(120)
    digest = security_layer.dossier_block(request)
    for identifiant in ("R1,", "R60,", "R119,", "R120"):
        assert identifiant in digest or identifiant in digest.replace(", ", ","), \
            f"identifiant {identifiant} absent du digest"
    assert "LISTE EXHAUSTIVE" in digest
    assert "120" in digest


def test_toutes_les_references_de_l_etape_11_sont_dans_le_digest():
    request = _request_avec_resultats(120)
    digest = security_layer.dossier_block(request)
    ligne = next(l for l in digest.splitlines() if "RÉFÉRENCES DE RÉSULTATS CITÉES" in l)
    assert ligne.count("R") >= 120


def test_toutes_les_cles_de_contenu_d_une_etape_sont_presentes():
    """Une étape dont le contenu vit sous une clé inattendue doit être entièrement visible."""
    request = CoherenceRequest(student_id="e", upstream_literature={
        "corpus": {"documents": ["Étude A sur le télétravail", "Étude B sur la productivité"]},
        "synthesis": {"texte": "La littérature oppose deux lectures du télétravail, l'une "
                               "organisationnelle et l'autre individuelle."},
        "bibliography": ["Durand, A. (2019). Télétravail et performance."],
        "verification_result": {"verified": True}})
    digest = security_layer._resume_etape(3, request.upstream_literature)
    assert "corpus" in digest
    assert "bibliography" in digest
    assert "Durand" in digest


def test_une_coupe_est_toujours_signalee():
    """Toute omission visible : jamais de troncature silencieuse."""
    valeur = [f"élément {i}" for i in range(30)]
    rendu = security_layer._compact_value(valeur, max_items=6)
    assert "+24 autre(s)" in rendu
    long_texte = "phrase " * 200
    assert security_layer._compact_value(long_texte).endswith("…")


def test_les_identifiants_sont_tries_naturellement():
    assert security_layer._rang_identifiant("R2") < security_layer._rang_identifiant("R10")
