"""Bibliographie déterministe de l'agent 4 : noms de fournisseurs remis dans le bon ordre.

Régression constatée en EXÉCUTION RÉELLE (chaîne 1→4, contrôle L10 du vérificateur) : les
fournisseurs renvoient « Nom Initiales » (« Mutiganda JC », « Jiang T »), et l'agent 4 prenait le
dernier mot pour le nom → la bibliographie affichait « JC, M. » au lieu de « Mutiganda, J. C. ».
"""

from problematization_agent.bibliography.styles import authors_apa, format_author


def test_nom_suivi_d_initiales_collées():
    assert format_author("Mutiganda JC") == "Mutiganda, J. C."
    assert format_author("Jiang T") == "Jiang, T."
    assert format_author("Blanc MÈ") == "Blanc, M. È."
    assert format_author("Parent-Lamarche A") == "Parent-Lamarche, A."


def test_forme_prenom_nom_particules_et_nom_seul():
    assert format_author("Marie Dupont") == "Dupont, M."
    assert format_author("Jan van der Berg") == "van der Berg, J."
    assert format_author("Graziotin, D.") == "Graziotin, D."
    assert format_author("Li") == "Li"          # casse mixte : jamais pris pour des initiales


def test_esperluette_et_virgule_serielle():
    assert authors_apa(["Elsamani Y", "Kajikawa Y"]) == "Elsamani, Y. & Kajikawa, Y."
    assert authors_apa(["Mutiganda JC", "Wiitavaara B", "Heiden M"]) == (
        "Mutiganda, J. C., Wiitavaara, B., & Heiden, M.")


# --- données réelles : noms d'auteurs renvoyés tels quels par les fournisseurs --------------------
# Cas relevés par le vérificateur sur une campagne réelle (chaîne agent 1→5).

def test_noms_d_auteurs_reels_rendus_correctement():
    from problematization_agent.bibliography.styles import format_author

    cas = {
        "Conradie Wj": "Conradie, W. J.",                     # initiales collées, 2e abaissée
        "Seán Ó Riain": "Ó Riain, S.",                        # particule « Ó » (nom composé)
        "Margaret\u2010Anne Storey": "Storey, M.-A.",         # prénom composé, tiret typographique
        "Jean\u2010Marc Peretti": "Peretti, J.-M.",
        "Mutiganda JC": "Mutiganda, J. C.",                   # bloc d'initiales en capitales
        "Boris Noé MANHOULI DANMOU": "Manhouli Danmou, B. N.",  # nom de famille en capitales, composé
        "FBA Diallo": "Diallo, F. B. A.",                     # initiales devant le nom
        "MM Barry": "Barry, M. M.",
        "Kai\u2010Kristian Kemell": "Kemell, K.-K.",
        "Li": "Li",                                           # nom court avec voyelle : jamais des initiales
    }
    for source, attendu in cas.items():
        assert format_author(source) == attendu, source
