from apps.backend.main import build_orchestrator
from packages.surveillance.domain.models import Detection, IncidentContext, Stage, structured


def test_complete_pipeline_emits_all_required_stages() -> None:
    result = build_orchestrator().process(
        Detection("junction-7", 0.94, 2, True, 0.92, "Airport Road")
    )
    assert result.status == "completed"
    assert [event.stage for event in result.events] == list(Stage)
    reasoning = result.events[3].payload
    planning = result.events[4].payload
    assert reasoning["severity"] == "critical"
    assert planning["actions"][1]["message"] == reasoning["alert_message"]
    serialized = structured(result)
    assert serialized["events"][0]["payload"]["occurred_at"].endswith("+00:00")


class ReviewedContext:
    def retrieve(self, detection: Detection) -> IncidentContext:
        return IncidentContext(
            policies=("Reviewed false alarms require a stricter boundary.",),
            contacts=("demo-contact",),
            procedures=("Record the outcome.",),
            prior_incident_count=1,
            reviewed_incidents=(
                {
                    "incident_id": "review-1",
                    "similarity": 0.8,
                    "influence_weight": 0.8,
                    "reviewed_at": "2026-09-27T10:00:00+00:00",
                    "reviewed_severity": "low",
                    "response_action": "none",
                    "false_alarm": True,
                    "reason": "Reviewed false alarm",
                    "original_decision": {
                        "severity": "high",
                        "response_action": "message",
                    },
                },
            ),
        )


def test_pipeline_reuses_persisted_learned_threshold_on_next_scan() -> None:
    orchestrator = build_orchestrator(context_repository=ReviewedContext())
    first = orchestrator.process(
        Detection(
            "junction-7",
            0.8,
            2,
            True,
            0.95,
            "Airport Road",
            organization_id="org-1",
        )
    )
    second = orchestrator.process(
        Detection(
            "junction-7",
            0.8,
            2,
            True,
            0.95,
            "Airport Road",
            organization_id="org-1",
        )
    )

    first_verification = first.events[1].payload
    second_verification = second.events[1].payload
    assert first_verification["threshold_profile_updated"] is True
    assert first_verification["decision_threshold"] > 0.68
    assert (
        second_verification["base_decision_threshold"] == first_verification["decision_threshold"]
    )
    assert second_verification["decision_threshold"] == first_verification["decision_threshold"]
    assert second_verification["threshold_profile_updated"] is False
    assert second_verification["threshold_factors"][0]["already_learned"] is True
