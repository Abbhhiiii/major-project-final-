import json
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from groq import BadRequestError

from packages.surveillance.adapters import LocalContextRepository
from packages.surveillance.agents import VerificationAgent
from packages.surveillance.domain.models import (
    Detection,
    SensorFrameSample,
    SensorReading,
    Severity,
)
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


class StrictFailureThenJsonCompletions(FakeCompletions):
    def __init__(self, content: str) -> None:
        super().__init__(content)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
            response = httpx.Response(400, request=request)
            raise BadRequestError(
                "Failed to validate JSON",
                response=response,
                body={"error": {"code": "json_validate_failed", "failed_generation": ""}},
            )
        return super().create(**kwargs)


class SequenceCompletions:
    def __init__(self, *contents: str) -> None:
        self.contents = list(contents)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        content = self.contents[min(len(self.requests) - 1, len(self.contents) - 1)]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def make_agent(content: dict):
    completions = FakeCompletions(json.dumps(content))
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return GroqReasoningAgent("test-key", "openai/gpt-oss-20b", client), completions


def no_memory_influence() -> dict:
    return {
        "applied": False,
        "incident_ids": [],
        "effect": "none",
        "explanation": "No reviewed incident influenced this decision.",
    }


@pytest.mark.parametrize("action", ["call", "message", "none"])
def test_groq_reasoning_uses_strict_schema_and_maps_decision(action: str) -> None:
    agent, completions = make_agent(
        {
            "severity": "high",
            "rationale": ["Policy requires escalation for a verified high-impact collision."],
            "response_action": action,
            "alert_message": "HIGH verified collision at MG Road; dispatch review required.",
            "memory_influence": no_memory_influence(),
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    verification = VerificationAgent().run(detection)
    context = LocalContextRepository().retrieve(detection)

    decision = agent.run(detection, verification, context)

    assert decision.severity == Severity.HIGH
    assert decision.provider == "groq"
    assert decision.model == "openai/gpt-oss-20b"
    assert decision.response_action == action
    assert decision.memory_influence["applied"] is False
    assert decision.memory_influence["weight"] == 0
    assert decision.notify_emergency_services is (action != "none")
    schema = completions.request["response_format"]["json_schema"]["schema"]
    assert "notify_emergency_services" not in schema["properties"]
    assert completions.request["response_format"]["json_schema"]["strict"] is True
    request_payload = json.loads(completions.request["messages"][1]["content"])
    assert set(request_payload) == {"scanning_layer", "verification_layer", "policy_retrieval"}
    assert request_payload["verification_layer"]["fused_probability"] > 0
    assert "sensor_readings" in request_payload["scanning_layer"]


def test_groq_records_which_reviewed_incident_influenced_the_decision() -> None:
    previous_id = "reviewed-incident-1"
    agent, _ = make_agent(
        {
            "severity": "low",
            "rationale": ["The matching reviewed false alarm applies to the current evidence."],
            "response_action": "none",
            "alert_message": "Reviewed low-risk event at MG Road; no escalation required.",
            "memory_influence": {
                "applied": True,
                "incident_ids": [previous_id],
                "effect": "lowered",
                "explanation": "A highly similar reviewed false alarm lowered the escalation level.",
            },
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    context = replace(
        LocalContextRepository().retrieve(detection),
        reviewed_incidents=(
            {"incident_id": previous_id, "similarity": 0.96, "influence_weight": 0.96},
        ),
    )

    decision = agent.run(detection, VerificationAgent().run(detection), context)

    assert decision.memory_influence == {
        "applied": True,
        "incident_ids": [previous_id],
        "effect": "lowered",
        "explanation": "A highly similar reviewed false alarm lowered the escalation level.",
        "weight": 0.96,
    }


def test_exact_review_match_deterministically_controls_final_action() -> None:
    agent, _ = make_agent(
        {
            "severity": "low",
            "rationale": ["Current fused evidence alone suggested no action."],
            "response_action": "none",
            "alert_message": "No action required for the event at MG Road.",
            "memory_influence": no_memory_influence(),
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.95, "MG Road")
    verification = VerificationAgent().run(detection)
    context = replace(
        LocalContextRepository().retrieve(detection),
        reviewed_incidents=(
            {
                "incident_id": "reviewed-exact",
                "similarity": 1.0,
                "influence_weight": 1.0,
                "reviewed_severity": "high",
                "response_action": "message",
                "false_alarm": False,
            },
        ),
    )

    decision = agent.run(detection, verification, context)

    assert verification.override_source == "visual_impact"
    assert decision.severity == Severity.HIGH
    assert decision.response_action == "message"
    assert decision.memory_influence["weight"] == 1.0
    assert decision.memory_influence["current_weight"] == 0.0
    assert decision.memory_influence["method"] == "similarity_weighted_human_review_v1"
    assert "100% matching reviewed intelligence" in decision.alert_message


def test_groq_prompt_summarizes_full_frame_timeline_and_review_memory() -> None:
    agent, completions = make_agent(
        {
            "severity": "medium",
            "rationale": ["Temporal sensor evidence warrants operator review."],
            "response_action": "none",
            "alert_message": "Sensor evidence at MG Road was recorded for operator review.",
            "memory_influence": no_memory_influence(),
        }
    )
    timeline = tuple(
        SensorFrameSample(
            frame_index=index,
            timestamp_ms=index * 40,
            readings=(
                SensorReading("smoke", index / 299, 0.9),
                SensorReading("audio", (299 - index) / 299, 0.8),
            ),
        )
        for index in range(300)
    )
    detection = replace(
        Detection("cam-1", 0.9, 2, True, 0.8, "MG Road"),
        sensor_timeline=timeline,
        sensor_scenario="rising-smoke",
    )
    context = replace(
        LocalContextRepository().retrieve(detection),
        reviewed_incidents=(
            {
                "incident_id": "reviewed-1",
                "similarity": 0.91,
                "influence_weight": 0.72,
                "scan": {
                    "confidence": 0.88,
                    "impact_score": 0.76,
                    "sensor_timeline": [
                        {"frame_index": index, "payload": "x" * 200} for index in range(300)
                    ],
                },
                "verification": {
                    "verified": True,
                    "fused_probability": 0.81,
                    "decision_threshold": 0.69,
                },
            },
        ),
    )

    agent.run(detection, VerificationAgent().run(detection), context)

    user_content = completions.request["messages"][1]["content"]
    payload = json.loads(user_content)
    scan = payload["scanning_layer"]
    summary = scan["sensor_timeline_summary"]
    assert "sensor_timeline" not in scan
    assert summary["frame_count"] == 300
    assert summary["duration_ms"] == 11_960
    assert summary["sensors"]["smoke"]["maximum_probability"] == 1.0
    assert summary["sensors"]["smoke"]["peak_frame_index"] == 299
    reviewed = payload["policy_retrieval"]["reviewed_incidents"][0]
    assert "sensor_timeline" not in reviewed["previous_scan_summary"]
    assert len(user_content) < 16_000
    assert completions.request["max_tokens"] == 1800


def test_groq_unretrieved_memory_citation_is_discarded_without_failing_pipeline() -> None:
    agent, _ = make_agent(
        {
            "severity": "low",
            "rationale": ["A previous case reduced the response."],
            "response_action": "none",
            "alert_message": "Low-risk event at MG Road; no escalation required.",
            "memory_influence": {
                "applied": True,
                "incident_ids": ["invented-incident"],
                "effect": "lowered",
                "explanation": "A previous case lowered the escalation level.",
            },
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")

    decision = agent.run(
        detection,
        VerificationAgent().run(detection),
        LocalContextRepository().retrieve(detection),
    )

    assert decision.memory_influence["applied"] is False
    assert decision.memory_influence["incident_ids"] == []
    assert decision.memory_influence["effect"] == "none"
    assert decision.memory_influence["ignored_unretrieved_incident_ids"] == [
        "invented-incident"
    ]


def test_groq_reasoning_rejects_notification_without_contact() -> None:
    agent, _ = make_agent(
        {
            "severity": "high",
            "rationale": ["Escalation requested."],
            "response_action": "call",
            "alert_message": "HIGH verified collision at MG Road; dispatch review required.",
            "memory_influence": no_memory_influence(),
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    verification = VerificationAgent().run(detection)
    context = LocalContextRepository().retrieve(detection)
    context = context.__class__(context.policies, (), context.procedures, 0)

    with pytest.raises(RuntimeError, match="without a retrieved contact"):
        agent.run(detection, verification, context)


def test_demo_reasoning_allows_action_without_contact() -> None:
    content = {
        "severity": "high",
        "rationale": ["Policy requires a simulated escalation."],
        "response_action": "call",
        "alert_message": "Verified incident at MG Road requires attention.",
        "memory_influence": no_memory_influence(),
    }
    completions = FakeCompletions(json.dumps(content))
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    agent = GroqReasoningAgent("test-key", "openai/gpt-oss-20b", client, allow_missing_contact=True)
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    context = LocalContextRepository().retrieve(detection)
    context = context.__class__(context.policies, (), context.procedures, 0)

    decision = agent.run(detection, VerificationAgent().run(detection), context)

    assert decision.response_action == "call"
    assert "explicitly simulated execution run" in completions.request["messages"][0]["content"]


def test_groq_falls_back_to_validated_json_mode_after_schema_failure() -> None:
    content = json.dumps(
        {
            "severity": "high",
            "rationale": ["Verified visual evidence and policy require attention."],
            "response_action": "message",
            "alert_message": "Verified incident at MG Road requires operator attention.",
            "memory_influence": no_memory_influence(),
        }
    )
    completions = StrictFailureThenJsonCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    agent = GroqReasoningAgent("test-key", "openai/gpt-oss-20b", client)
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")

    decision = agent.run(
        detection,
        VerificationAgent().run(detection),
        LocalContextRepository().retrieve(detection),
    )

    assert decision.response_action == "message"
    assert completions.requests[0]["response_format"]["type"] == "json_schema"
    assert "response_format" not in completions.requests[1]


def test_groq_validates_json_wrapped_by_unconstrained_fallback() -> None:
    content = {
        "severity": "medium",
        "rationale": ["The verified event requires operator review."],
        "response_action": "message",
        "alert_message": "Verified incident at MG Road requires operator review.",
        "memory_influence": no_memory_influence(),
    }

    output = GroqReasoningAgent._parse_output(f"```json\n{json.dumps(content)}\n```")

    assert output.severity == Severity.MEDIUM
    assert output.response_action == "message"


def test_groq_normalizes_common_structural_drift_without_changing_core_decision() -> None:
    output = GroqReasoningAgent._parse_output(
        json.dumps(
            {
                "severity": "HIGH",
                "rationale": "Verified evidence requires operator attention.",
                "action": "message",
                "message": "Verified incident at MG Road requires operator attention.",
                "unexpected_commentary": "ignored",
            }
        )
    )

    assert output.severity == Severity.HIGH
    assert output.response_action == "message"
    assert output.rationale == ["Verified evidence requires operator attention."]
    assert output.memory_influence.applied is False


def test_groq_repairs_a_malformed_core_decision_with_a_second_model_response() -> None:
    valid = json.dumps(
        {
            "severity": "medium",
            "rationale": ["Verified evidence requires an operator review."],
            "response_action": "message",
            "alert_message": "Verified incident at MG Road requires operator review.",
            "memory_influence": no_memory_influence(),
        }
    )
    completions = SequenceCompletions('{"severity":"unknown"}', valid)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    agent = GroqReasoningAgent("test-key", "openai/gpt-oss-20b", client)
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")

    decision = agent.run(
        detection,
        VerificationAgent().run(detection),
        LocalContextRepository().retrieve(detection),
    )

    assert decision.severity == Severity.MEDIUM
    assert decision.response_action == "message"
    assert len(completions.requests) == 2
    assert completions.requests[1]["response_format"]["json_schema"]["name"].startswith(
        "repaired_"
    )


@pytest.mark.parametrize("action", ["call", "message"])
def test_groq_rejects_escalation_for_unverified_event(action: str) -> None:
    agent, _ = make_agent(
        {
            "severity": "high",
            "rationale": ["Escalation requested."],
            "response_action": action,
            "alert_message": "Incident at MG Road requires attention.",
            "memory_influence": no_memory_influence(),
        }
    )
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    verification = replace(VerificationAgent().run(detection), verified=False)
    context = LocalContextRepository().retrieve(detection)
    with pytest.raises(RuntimeError, match="unverified event"):
        agent.run(detection, verification, context)
