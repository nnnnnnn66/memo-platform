"""Test 12 — Consommation excessive : les bornes d'entrée s'appliquent."""

import pytest

from subject_agent.core.errors import ErrorState, PipelineError
from subject_agent.pipeline import input_validation
from subject_agent.pipeline.input_controller import prepare
from subject_agent.schemas.input import SubjectRequest


def test_entree_trop_volumineuse_rejetee(settings):
    huge = "a" * (settings.limits.max_input_size + 1)
    request = prepare(SubjectRequest(student_id="x", subject_text=huge))
    with pytest.raises(PipelineError) as exc:
        input_validation.validate(request, settings.limits)
    assert exc.value.state == ErrorState.RESOURCE_LIMIT


def test_sortie_vide_rejetee():
    from subject_agent.pipeline import output_parser
    with pytest.raises(PipelineError) as exc:
        output_parser.extract_json("")
    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR


def test_json_multi_ligne_dans_fence_extrait_en_entier():
    """Régression : la fence ```json ne doit pas tronquer l'objet au premier « } »."""
    from subject_agent.pipeline import output_parser
    txt = 'bla\n```json\n{\n  "a": {\n    "b": 1\n  },\n  "c": 2\n}\n```\nfin'
    assert output_parser.extract_json(txt) == {"a": {"b": 1}, "c": 2}
