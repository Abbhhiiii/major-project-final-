import json
from types import SimpleNamespace

import pytest

from packages.surveillance.adapters import LocalContextRepository
from packages.surveillance.agents import VerificationAgent
from packages.surveillance.domain.models import Detection, Severity
from packages.surveillance.infrastructure.groq_reasoning import GroqReasoningAgent


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


def make_agent(content: dict):
    completions = FakeCompletions(json.dumps(content))
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return GroqReasoningAgent("test-key", "openai/gpt-oss-20b", client), completions


def test_groq_reasoning_uses_strict_schema_and_maps_decision() -> None:
    agent, completions = make_agent(
        {
            "severity": "high",
            "rationale": ["Policy requires escalation for a verified high-impact collision."],
            "notify_emergency_services": True,
            "alert_message": "HIGH verified collision at MG Road; dispatch review required.",
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    verification = VerificationAgent().run(detection)
    context = LocalContextRepository().retrieve(detection)

    decision = agent.run(detection, verification, context)

    assert decision.severity == Severity.HIGH
    assert decision.provider == "groq"
    assert decision.model == "openai/gpt-oss-20b"
    assert completions.request["response_format"]["json_schema"]["strict"] is True
    assert "retrieved_context" in completions.request["messages"][1]["content"]


def test_groq_reasoning_rejects_notification_without_contact() -> None:
    agent, _ = make_agent(
        {
            "severity": "high",
            "rationale": ["Escalation requested."],
            "notify_emergency_services": True,
            "alert_message": "HIGH verified collision at MG Road; dispatch review required.",
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    verification = VerificationAgent().run(detection)
    context = LocalContextRepository().retrieve(detection)
    context = context.__class__(context.policies, (), context.procedures, 0)

    with pytest.raises(RuntimeError, match="without a retrieved contact"):
        agent.run(detection, verification, context)
