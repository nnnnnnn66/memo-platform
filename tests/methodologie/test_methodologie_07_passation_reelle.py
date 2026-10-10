"""Passation RÉELLE vers l'agent 8 : hypothèses et revue de littérature telles que produites.

Né d'un échec de chaîne réel : l'agent 8 refusait la sortie de l'agent 7 (liste d'OBJETS
d'hypothèses, 5 erreurs « Input should be a valid string ») et la revue de littérature structurée de
l'agent 3 (dict) au lieu de les convertir.
"""


def _request(**kw):
    from methodology_diagnostic_agent.schemas.input import MethodologyRequest
    return MethodologyRequest(student_id="e", discipline="Gestion", **kw)


def test_hypotheses_en_objets_converties_en_formulations():
    """Forme réelle de la sortie de l'agent 7 : une liste d'objets."""
    hyp = [
        {"id": "H1", "formulation": "La coordination est associée à la productivité.",
         "linked_to": "Objectif général", "sources": ["problématique fournie"]},
        {"id": "H2", "formulation": "L'intensité du télétravail module la productivité.",
         "linked_to": "Objectif spécifique 1"},
    ]
    req = _request(hypotheses=hyp)
    assert req.hypotheses == ["La coordination est associée à la productivité.",
                              "L'intensité du télétravail module la productivité."]
    assert req.effective_hypotheses() == req.hypotheses


def test_revue_de_litterature_structuree_convertie_en_texte():
    """Forme réelle de la sortie de l'agent 3 : un objet de synthèse."""
    req = _request(literature_review={
        "state_of_knowledge": "Les travaux convergent sur le rôle de la coordination.",
        "controversies": ["L'effet varie selon les contextes.", "Les mesures diffèrent."],
    })
    assert "coordination" in req.literature_review
    assert "contextes" in req.literature_review


def test_chaines_simples_inchangees():
    req = _request(hypotheses=["H1 : texte", "  ", "H2 : texte"], literature_review="Texte simple.")
    assert req.hypotheses == ["H1 : texte", "H2 : texte"]
    assert req.literature_review == "Texte simple."


def test_objet_sans_formulation_ignore():
    """Un objet sans formulation ne doit pas introduire de texte parasite (ni l'identifiant seul)."""
    req = _request(hypotheses=[{"id": "H1"}, {"formulation": "Texte utile."}])
    assert req.hypotheses == ["Texte utile."]
