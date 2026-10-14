"""F5 (étape 5) — SOURCE des délimitations : attribuée ET citée ⇒ acceptée ; sans source ⇒ refusée.

Défaut réel : sur un dossier neuf, l'agent repliait dans `scope_and_boundaries` une délimitation
venue du contexte de l'étudiant (« Bouaké — marchés de Sokoura et de Koko ») en l'abrégeant, sans la
citer. Le contrôle F5 la signalait — à juste titre, puisqu'elle ne se retrouvait plus telle quelle
dans les données. Deux corrections :
  1. le prompt impose d'ATTRIBUER et de CITER (mot pour mot, entre guillemets) ;
  2. le garde-fou ACCEPTE une délimitation qui porte une citation EXACTE d'un libellé de l'étudiant.
La règle reste STRICTE : sans citation ni recoupement verbatim, la délimitation est refusée.
"""

from types import SimpleNamespace

from research_question_agent.analysis import question_rules as qr
from research_question_agent.pipeline import formulation_checks
from research_question_agent.schemas.question import ScopeAndBoundaries

# Contexte réellement transmis par l'étudiant (dossier mobile-money-bouake-v5).
PROVIDED = ("Sujet : L'adoption du paiement mobile (mobile money) par les commerçantes des marchés "
            "de Bouaké : usages, freins et effets sur leur activité commerciale\n"
            "Pays : Côte d'Ivoire\n"
            "Zone géographique : Bouaké, district de la Vallée du Bandama — marchés de Sokoura "
            "et de Koko\n"
            "Période : 2018-2025\n"
            "Contexte : Étude de terrain auprès de commerçantes des marchés de Sokoura et de Koko "
            "à Bouaké.")


class _Request:
    def all_provided_text(self) -> str:
        return PROVIDED

    def effective_subject(self) -> str:
        return ""


def _formulation(scope):
    """Formulation minimale : seuls les champs lus par le contrôle F5 importent."""
    return SimpleNamespace(
        main_research_question=("Comment se caractérisent les usages du paiement mobile chez les "
                               "commerçantes des marchés ?"),
        secondary_research_questions=[],
        scope_and_boundaries=scope,
    )


def _f5(scope) -> list[str]:
    return [v for v in formulation_checks.apply(_formulation(scope), _Request(), "")
            if v.startswith("F5")]


# --- (a) attribuée ET citée ⇒ acceptée ---------------------------------------------------------

def test_delimitation_attribuee_et_citee_acceptee():
    """L'agent abrège la zone dans sa langue MAIS cite mot pour mot le libellé de l'étudiant."""
    scope = ScopeAndBoundaries(
        geo="Bouaké — marchés de Sokoura et de Koko (étudiant : « Bouaké, district de la Vallée "
            "du Bandama — marchés de Sokoura et de Koko »)")
    assert qr.unsourced_boundaries(scope, PROVIDED) == {}
    assert _f5(scope) == []
    assert scope.added_without_source is False


def test_citation_exacte_reconnue_par_le_garde_fou():
    assert qr.is_cited_from_student(
        "zone (« Bouaké, district de la Vallée du Bandama »)", qr._normalize(PROVIDED))
    # Guillemets droits acceptés aussi.
    assert qr.cited_fragments('zone ("marchés de Sokoura et de Koko")') == ["marchés de Sokoura et de Koko"]


# --- (b) sans source ⇒ refusée -----------------------------------------------------------------

def test_delimitation_sans_source_refusee():
    """La zone abrégée mais NON citée (le cas du défaut reproduit) est signalée."""
    scope = ScopeAndBoundaries(geo="Bouaké — marchés de Sokoura et de Koko")
    assert "geo" in qr.unsourced_boundaries(scope, PROVIDED)
    assert _f5(scope), "une délimitation sans source doit déclencher F5"
    assert scope.added_without_source is True


def test_delimitation_inventee_refusee():
    scope = ScopeAndBoundaries(geo="Abidjan")
    assert "geo" in qr.unsourced_boundaries(scope, "sujet sans mention géographique")


def test_citation_fabriquee_refusee():
    """Une citation qui ne se retrouve PAS dans les données ne vaut rien (citation inventée)."""
    scope = ScopeAndBoundaries(geo="Sokoura et Koko (« marchés de Ferkessédougou »)")
    assert "geo" in qr.unsourced_boundaries(scope, PROVIDED)
    assert not qr.is_cited_from_student("« marchés de Ferkessédougou »", qr._normalize(PROVIDED))


# --- non-régression : la règle stricte tient toujours ------------------------------------------

def test_zone_composee_fournie_par_champs_distincts_toujours_acceptee():
    scope = ScopeAndBoundaries(geo="Côte d'Ivoire, Bouaké")
    assert qr.unsourced_boundaries(scope, PROVIDED) == {}


# --- « manque fantôme » : ne pas déclarer manquante une délimitation fournie ---------------------

def _derive_missing(scope):
    from research_question_agent.pipeline import campaign

    request = SimpleNamespace(
        target_population="", geographical_area="", country="", study_period="",
        all_provided_text=lambda: PROVIDED)
    pre = {"defaults_used": []}
    feasibility = SimpleNamespace(manques=[])
    missing, _ = campaign._derived(request, pre, feasibility, scope)
    return missing


def test_population_fournie_n_est_pas_declaree_manquante():
    """Le sujet cite « commerçantes des marchés de Sokoura et de Koko » : ce n'est PAS un manque."""
    scope = ScopeAndBoundaries(geo="Bouaké, district de la Vallée du Bandama — marchés de Sokoura et de Koko",
                               temps="", population="commerçantes des marchés de Sokoura et de Koko")
    missing = _derive_missing(scope)
    assert not any("population" in m for m in missing), missing


def test_population_absente_est_declaree_manquante():
    scope = ScopeAndBoundaries(geo="", temps="", population="")
    assert any("population" in m for m in _derive_missing(scope))


def test_population_inventee_reste_declaree_manquante():
    """Une population NON traçable n'est pas « fournie » : elle reste un manque (règle stricte)."""
    scope = ScopeAndBoundaries(geo="", temps="", population="les fonctionnaires centraux")
    assert any("population" in m for m in _derive_missing(scope))
