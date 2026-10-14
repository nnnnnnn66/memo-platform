"""Étape 4 — SOURCE des délimitations du constat (zone, population).

Même famille de défaut que F5 (étape 5) : l'agent replie dans sa production une précision venue du
contexte de l'étudiant sans l'attribuer ni la citer. Le garde-fou R10 refuse une délimitation qui ne
recoupe AUCUNE donnée de l'étudiant ; il ACCEPTE (règle « attribuée ET citée ⇒ acceptée ») une
délimitation qui reprend le libellé de l'étudiant ou le cite mot pour mot entre guillemets.
"""

from types import SimpleNamespace

from problematization_agent.pipeline import business_validation as bv
from problematization_agent.schemas.output import ProblemStatus, ProblematizationOutput
from problematization_agent.schemas.problem import ProblemMapping

PROVIDED = ("Sujet : L'adoption du paiement mobile (mobile money) par les commerçantes des marchés "
            "de Bouaké\nZone géographique : Bouaké, district de la Vallée du Bandama — marchés de "
            "Sokoura et de Koko\nContexte : Étude de terrain auprès de commerçantes des marchés de "
            "Sokoura et de Koko à Bouaké.")


class _Request:
    subject_text = ""

    def untrusted_texts(self) -> dict:
        return {"subject_text": PROVIDED, "geographical_scope": PROVIDED}


def _mapping(zone: str, population: str = "") -> ProblemMapping:
    return ProblemMapping(zone_geographique=zone, population=population)


# --- (a) attribuée ET citée ⇒ acceptée ---------------------------------------------------------

def test_delimitation_attribuee_et_citee_acceptee():
    mapping = _mapping(
        zone="Le périmètre annoncé par l'étudiant (« Bouaké, district de la Vallée du Bandama — "
             "marchés de Sokoura et de Koko »)")
    assert bv.unsourced_delimitations(mapping, PROVIDED) == {}


def test_delimitation_reprise_de_l_etudiant_acceptee():
    mapping = _mapping(zone="Bouaké, district de la Vallée du Bandama — marchés de Sokoura et de Koko",
                       population="commerçantes des marchés de Sokoura et de Koko")
    assert bv.unsourced_delimitations(mapping, PROVIDED) == {}


# --- (b) sans source ⇒ refusée -----------------------------------------------------------------

def test_zone_etrangere_refusee():
    mapping = _mapping(zone="Dakar, Sénégal")
    assert "zone_geographique" in bv.unsourced_delimitations(mapping, PROVIDED)


def test_population_inventee_refusee():
    mapping = _mapping(zone="Bouaké", population="les fonctionnaires de l'administration centrale")
    assert "population" in bv.unsourced_delimitations(mapping, PROVIDED)


def test_zone_vide_n_est_pas_signalee():
    # Un champ vide n'est pas une invention : c'est un manque, déclaré dans missing_elements.
    assert bv.unsourced_delimitations(_mapping(zone="", population=""), PROVIDED) == {}


# --- intégration : le contrôle R10 est bien branché dans validate_semantics ---------------------

def _output(mapping: ProblemMapping) -> ProblematizationOutput:
    return ProblematizationOutput(status=ProblemStatus.ready_for_verification, problem_mapping=mapping)


_INDEX = SimpleNamespace(doc_ids=set(), quote_ok=lambda *a, **k: True)


def _r10(output) -> list[str]:
    return [v for v in bv.validate_semantics(output, _Request(), _INDEX) if v.startswith("R10")]


def test_r10_absent_quand_la_delimitation_est_sourcee():
    output = _output(_mapping(zone="Bouaké, district de la Vallée du Bandama — marchés de Sokoura et de Koko",
                              population="commerçantes des marchés de Sokoura et de Koko"))
    assert _r10(output) == []


def test_r10_declenche_quand_la_delimitation_est_inventee():
    output = _output(_mapping(zone="Dakar, Sénégal"))
    violations = _r10(output)
    assert violations, "une délimitation sans source doit déclencher R10"
    assert "Dakar" in violations[0]
