from apps.backend.main import build_orchestrator
from packages.surveillance.domain.models import Detection, Stage, structured


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
