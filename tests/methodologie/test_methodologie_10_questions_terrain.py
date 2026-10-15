"""L'agent ne rend à l'étudiante que des questions de TERRAIN (consigne du porteur).

Défaut réel constaté avant démonstration : l'étape 6 transformait chacune de ses ambiguïtés en
question (« Pouvez-vous préciser : Formulation orientée… »), et l'étape 8 demandait à l'étudiante de
« valider l'adoption d'une approche mixte ou de restreindre le travail au volet quantitatif ».
Or l'étudiante vient justement parce qu'elle ne sait pas : un CHOIX de méthode appartient à la
plateforme, qui le tranche et le DÉCLARE — elle peut corriger en reprenant l'étape. Seul le TERRAIN
(accès, autorisations, ressources, données réellement disponibles) est de son ressort.
"""
from methodology_diagnostic_agent.pipeline.campaign import _est_question_de_terrain


def test_les_choix_de_methode_ne_sont_pas_rendus_a_l_etudiante():
    for question in (
        "Valider l'adoption d'une approche mixte, ou restreindre le travail au volet quantitatif",
        "Décider des critères de délimitation des secteurs concernés et non concernés",
        "Valider le logiciel et les compétences SIG/télédétection retenus",
        "Pouvez-vous préciser : Formulation orientée : la question présuppose l'existence de...",
        "La borne 2025 n'est pas justifiée au regard de la disponibilité des données",
    ):
        assert not _est_question_de_terrain(question), question


def test_le_terrain_reste_demande():
    for question in (
        "Confirmez-vous l'accès effectif aux documents et registres des opérations ?",
        "Avez-vous l'autorisation d'enquêter auprès des usagers ?",
        "De combien de temps et de quels moyens disposez-vous pour le terrain ?",
    ):
        assert _est_question_de_terrain(question), question
