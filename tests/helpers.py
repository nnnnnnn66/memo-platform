"""Fabriques d'objets de sortie pour les tests."""

import json

VERIFIER_VERIFIED = {
    "agent": "subject_verifier",
    "version": "1.0",
    "verdict": "verified",
    "controls": [{"code": "C1", "resultat": "ok", "detail": ""}],
    "corrections": [],
    "flags": [],
}


def subject_output(subject_text, status="ready_for_verification", **overrides):
    out = {
        "agent": "subject_agent",
        "version": "1.0",
        "status": status,
        "subject": {"original": subject_text, "reformulated": ""},
        "research_context": {
            "domain": "domaine", "object_of_study": "objet d'étude", "population": "",
            "geographical_scope": "", "temporal_scope": "", "phenomenon": "",
        },
        "key_concepts": [],
        "initial_justification": "",
        "feasibility": {"status": "unknown", "concerns": []},
        "missing_information": [],
        "questions_for_student": [],
        "identified_ambiguities": [],
        "identified_limits": [],
        "evidence": [],
        "confidence": {"overall": 0.5},
        "validation": {"verified": False, "verifier_status": "pending"},
    }
    out.update(overrides)
    return out


def as_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


class StubLLM:
    """LLM simulé : renvoie une file de réponses prédéfinies. Reproductible, sans réseau."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.sent = []

    def complete(self, system, user):
        self.sent.append({"system": system, "user": user})
        if not self.responses:
            raise AssertionError("StubLLM: plus de réponses disponibles")
        self.calls += 1
        return self.responses.pop(0)
