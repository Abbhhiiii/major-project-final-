import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF

from apps.backend.main import create_app
from packages.surveillance.agents import ReasoningAgent
from packages.surveillance.infrastructure.config import Settings
from packages.surveillance.perception.models import DetectorOutput, VideoFrame
from packages.surveillance.perception.synthetic_sensors import SyntheticSensorStreamGenerator


class StubFrameReader:
    def frames(self, path: Path, sample_fps: float) -> tuple[int, Iterator[VideoFrame]]:
        frames = [VideoFrame(0, 0, object()), VideoFrame(10, 500, object())]
        return len(frames), iter(frames)


class ThirtyFrameReader:
    def frames(self, path: Path, sample_fps: float) -> tuple[int, Iterator[VideoFrame]]:
        frames = [VideoFrame(index, index * 33, object()) for index in range(30)]
        return len(frames), iter(frames)


class StubAccidentDetector:
    def detect(
        self, frame: VideoFrame, *, camera_id: str, location: str
    ) -> tuple[DetectorOutput, ...]:
        if frame.timestamp_ms != 500:
            return ()
        return (DetectorOutput(0.95, 0.91, 2, True, frame.timestamp_ms, location),)


class StubNoDetectionDetector:
    def detect(
        self, frame: VideoFrame, *, camera_id: str, location: str
    ) -> tuple[DetectorOutput, ...]:
        return ()


class MultimodalSyntheticSensorGenerator(SyntheticSensorStreamGenerator):
    def scenario_for(self, video_id: str, requested: str = "randomized") -> str:
        return "both_high"


def make_client(tmp_path: Path, *, detector: Any = None, frame_reader: Any = None) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_directory=tmp_path / "uploads",
        policy_directory=tmp_path / "policies",
        report_directory=tmp_path / "reports",
        accident_model_path=None,
        playback_speed=0,
    )
    return TestClient(
        create_app(
            settings,
            detector=detector,
            frame_reader=frame_reader,
            reasoning_service=ReasoningAgent(),
        )
    )


def detection_payload() -> dict[str, object]:
    return {
        "camera_id": "junction-7",
        "confidence": 0.94,
        "vehicle_count": 2,
        "stopped_vehicle": True,
        "impact_score": 0.92,
        "location": "Airport Road",
    }


def authorize(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Test Organization",
            "email": f"test-{uuid4()}@example.test",
            "password": "test-password-123",
        },
    )
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


def test_processing_persists_history_and_updates_analytics(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        response = client.post("/api/v1/incidents/process", json=detection_payload())
        assert response.status_code == 200
        incident_id = response.json()["incident_id"]

        history = client.get("/api/v1/incidents").json()
        assert history["count"] == 1
        assert history["items"][0]["incident_id"] == incident_id
        assert history["items"][0]["rationale"]

        detail = client.get(f"/api/v1/incidents/{incident_id}")
        assert detail.status_code == 200
        assert detail.json()["alert_message"].startswith("CRITICAL")

        audit = client.get(f"/api/v1/incidents/{incident_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["reasoning_provider"] == "deterministic"
        assert audit.json()["decision"]["alert_message"] == detail.json()["alert_message"]
        assert audit.json()["plan"]["actions"]
        assert audit.json()["retrieval"]["scan_snapshot"]["confidence"] == 0.94
        assert audit.json()["retrieval"]["verification_snapshot"]["contributions"]["visual"]

        analytics = client.get("/api/v1/analytics/summary").json()
        assert analytics == {"total_incidents": 1, "by_severity": {"critical": 1}}

        deliveries = client.get(f"/api/v1/incidents/{incident_id}/deliveries").json()
        assert deliveries["count"] == 2
        report_record = next(
            item for item in deliveries["items"] if item["action_kind"] == "pdf_report"
        )
        assert report_record["message"] == detail.json()["alert_message"]
        report = client.get(f"/api/v1/incidents/{incident_id}/report")
        assert report.status_code == 200
        assert report.content.startswith(b"%PDF")


def test_sse_endpoint_emits_dashboard_ready_pipeline_events(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        response = client.post("/api/v1/incidents/process/stream", json=detection_payload())
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.text.count("event:") == 7
        assert "event: verification" in response.text
        assert "event: memory" in response.text


def test_sse_pipeline_exposes_sensor_fusion_to_reasoning(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        payload = detection_payload()
        payload["sensor_readings"] = [
            {"sensor_type": "smoke", "probability": 0.81, "reliability": 0.9, "age_ms": 100},
            {"sensor_type": "audio", "probability": 0.86, "reliability": 0.92, "age_ms": 80},
        ]
        response = client.post("/api/v1/incidents/process/stream", json=payload)
        assert response.status_code == 200
        events = [
            json.loads(line.removeprefix("data: "))
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        detection = next(item for item in events if item["stage"] == "detection")
        verification = next(item for item in events if item["stage"] == "verification")
        assert {item["sensor_type"] for item in detection["payload"]["sensor_readings"]} == {
            "smoke",
            "audio",
        }
        assert (
            verification["payload"]["fused_probability"]
            >= verification["payload"]["decision_threshold"]
        )
        assert "smoke" in verification["payload"]["contributions"]


def test_missing_incident_returns_not_found(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        response = client.get("/api/v1/incidents/not-a-real-id")
        assert response.status_code == 404


def test_review_memory_is_retrieved_and_tenant_isolated(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        first = client.post("/api/v1/incidents/process", json=detection_payload()).json()
        incident_id = first["incident_id"]
        review = {
            "severity": "low",
            "response_action": "none",
            "reason": "Operator confirmed planned maintenance activity",
            "false_alarm": True,
        }
        saved = client.put(f"/api/v1/incidents/{incident_id}/review", json=review)
        assert saved.status_code == 200
        assert (
            client.get(f"/api/v1/incidents/{incident_id}/review").json()["reason"]
            == review["reason"]
        )
        second = client.post("/api/v1/incidents/process", json=detection_payload()).json()
        verification = second["events"][1]["payload"]
        context = second["events"][2]["payload"]
        assert verification["base_decision_threshold"] == 0.68
        assert verification["decision_threshold"] > 0.68
        assert verification["threshold_adjustment"] > 0
        assert verification["threshold_factors"][0]["incident_id"] == incident_id
        assert context["reviewed_incidents"][0]["incident_id"] == incident_id
        assert context["reviewed_incidents"][0]["reviewed_severity"] == "low"
        assert context["reviewed_incidents"][0]["verification"]["verified"] is True
        client.put(
            f"/api/v1/incidents/{second['incident_id']}/review",
            json={
                "severity": "high",
                "response_action": "message",
                "reason": "Operator confirmed this newer matching incident needs attention",
                "false_alarm": False,
            },
        )
        third = client.post("/api/v1/incidents/process", json=detection_payload()).json()
        best_matches = third["events"][2]["payload"]["reviewed_incidents"]
        assert len(best_matches) == 1
        assert best_matches[0]["incident_id"] == second["incident_id"]
        different = {**detection_payload(), "location": "Another location"}
        assert (
            client.post("/api/v1/incidents/process", json=different).json()["events"][2]["payload"][
                "reviewed_incidents"
            ]
            == []
        )
        authorize(client)
        assert client.get(f"/api/v1/incidents/{incident_id}/review").status_code == 404
        assert client.put(f"/api/v1/incidents/{incident_id}/review", json=review).status_code == 404
        assert (
            client.post("/api/v1/incidents/process", json=detection_payload()).json()["events"][2][
                "payload"
            ]["reviewed_incidents"]
            == []
        )


def test_review_memory_exposes_weighted_full_sensor_profile_match(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        first_payload = {
            **detection_payload(),
            "sensor_readings": [
                {"sensor_type": "smoke", "probability": 0.82, "reliability": 0.9, "age_ms": 100},
                {"sensor_type": "audio", "probability": 0.76, "reliability": 0.86, "age_ms": 200},
            ],
        }
        first = client.post("/api/v1/incidents/process", json=first_payload).json()
        client.put(
            f"/api/v1/incidents/{first['incident_id']}/review",
            json={
                "severity": "low",
                "response_action": "none",
                "reason": "Operator confirmed a non-emergency maintenance event",
                "false_alarm": True,
            },
        )
        second_payload = {
            **first_payload,
            "confidence": 0.9,
            "impact_score": 0.89,
            "sensor_readings": [
                {"sensor_type": "smoke", "probability": 0.8, "reliability": 0.88, "age_ms": 180},
                {"sensor_type": "audio", "probability": 0.72, "reliability": 0.84, "age_ms": 260},
            ],
        }
        second = client.post("/api/v1/incidents/process", json=second_payload).json()
        match = second["events"][2]["payload"]["reviewed_incidents"][0]

        assert match["match_method"] == "weighted_full_sensor_profile_v1"
        assert match["influence_weight"] == match["similarity"]
        assert match["similarity"] > 0.9
        assert {item["key"] for item in match["feature_matches"]} == {
            "visual.confidence",
            "visual.impact_score",
            "sensor.smoke.probability",
            "sensor.smoke.reliability",
            "sensor.smoke.freshness",
            "sensor.audio.probability",
            "sensor.audio.reliability",
            "sensor.audio.freshness",
        }
        assert sum(item["weight"] for item in match["feature_matches"]) == pytest.approx(1)


def test_dashboard_origin_is_allowed_by_cors(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.options(
            "/api/v1/incidents",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_video_upload_playback_and_detector_handoff(tmp_path: Path) -> None:
    video_content = b"mock-mp4-video-content"
    with make_client(tmp_path) as client:
        authorize(client)
        upload = client.post(
            "/api/v1/videos",
            files={"video": ("junction.mp4", video_content, "video/mp4")},
        )
        assert upload.status_code == 201
        video = upload.json()

        playback = client.get(video["playback_path"], headers={"Range": "bytes=0-3"})
        assert playback.status_code == 206
        assert playback.content == video_content[:4]

        detection = client.post(
            f"/api/v1/videos/{video['video_id']}/detections",
            json={
                "camera_id": "cam-upload-1",
                "confidence": 0.94,
                "impact_score": 0.92,
                "vehicle_count": 2,
                "stopped_vehicle": True,
                "frame_timestamp_ms": 12400,
                "location": "Airport Road",
            },
        )
        assert detection.status_code == 200
        incident_id = detection.json()["incident_id"]
        incident = client.get(f"/api/v1/incidents/{incident_id}").json()
        assert incident["source_video_id"] == video["video_id"]
        assert incident["frame_timestamp_ms"] == 12400


def test_generated_sensor_stream_can_start_pipeline_without_cv_detection(tmp_path: Path) -> None:
    with make_client(
        tmp_path, detector=StubNoDetectionDetector(), frame_reader=ThirtyFrameReader()
    ) as client:
        authorize(client)
        client.app.state.video_processor.sensor_generator = MultimodalSyntheticSensorGenerator()
        upload = client.post(
            "/api/v1/videos",
            files={"video": ("image3-accident-test.mp4", b"demo-video", "video/mp4")},
        )
        video_id = upload.json()["video_id"]
        started = client.post(
            f"/api/v1/videos/{video_id}/process",
            json={"camera_id": "cam-sensor", "location": "Sensor Test Zone"},
        )
        assert started.status_code == 202
        history = client.get("/api/v1/incidents").json()
        assert history["count"] == 1
        audit = client.get(f"/api/v1/incidents/{history['items'][0]['incident_id']}/audit").json()
        assert set(audit["retrieval"]["scan_snapshot"]["candidate_sources"]) == {
            "smoke",
            "audio",
        }


def test_generated_sensor_stream_is_bound_to_video_audited_and_downloadable(tmp_path: Path) -> None:
    with make_client(
        tmp_path, detector=StubNoDetectionDetector(), frame_reader=ThirtyFrameReader()
    ) as client:
        authorize(client)
        client.app.state.video_processor.sensor_generator = MultimodalSyntheticSensorGenerator()
        video = client.post(
            "/api/v1/videos",
            files={"video": ("unmapped-demo.mp4", b"demo-video", "video/mp4")},
        ).json()
        started = client.post(
            f"/api/v1/videos/{video['video_id']}/process",
            json={"camera_id": "cam-generated-sensor", "location": "Metadata Test Zone"},
        )
        assert started.status_code == 202
        incident = client.get("/api/v1/incidents").json()["items"][0]
        audit = client.get(f"/api/v1/incidents/{incident['incident_id']}/audit").json()
        scan = audit["retrieval"]["scan_snapshot"]
        assert scan["sensor_scenario"] == "both_high"
        assert len(scan["sensor_timeline"]) == 30
        assert {item["source"] for item in scan["sensor_readings"]} == {"synthetic_live"}
        stream = client.get(f"/api/v1/videos/{video['video_id']}/sensor-stream")
        assert stream.status_code == 200
        assert stream.json()["frame_count"] == 30
        assert stream.json()["scenario"] == "both_high"
        assert len(stream.json()["samples"]) == 30


def test_video_upload_rejects_unsupported_content(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        response = client.post(
            "/api/v1/videos",
            files={"video": ("notes.txt", b"not video", "text/plain")},
        )
        assert response.status_code == 422


def test_background_frame_processing_reports_progress_and_creates_incident(
    tmp_path: Path,
) -> None:
    with make_client(
        tmp_path, detector=StubAccidentDetector(), frame_reader=StubFrameReader()
    ) as client:
        authorize(client)
        upload = client.post(
            "/api/v1/videos",
            files={"video": ("junction.mp4", b"video-bytes", "video/mp4")},
        ).json()
        start = client.post(
            f"/api/v1/videos/{upload['video_id']}/process",
            json={"camera_id": "cam-7", "location": "Airport Road"},
        )
        assert start.status_code == 202
        job_id = start.json()["job_id"]

        job = client.get(f"/api/v1/processing-jobs/{job_id}").json()
        assert job["status"] == "completed"
        assert job["progress_percent"] == 100
        assert job["frames_processed"] == 2
        assert job["detections_found"] == 1

        events = client.get(f"/api/v1/processing-jobs/{job_id}/events")
        assert events.status_code == 200
        assert '"status":"completed"' in events.text
        assert events.text.count("event: sensor") == 2
        assert '"frame_index":0' in events.text
        assert '"frame_index":10' in events.text
        assert events.text.count("event: pipeline") == 7
        assert '"stage":"reasoning"' in events.text
        assert events.text.index('"stage":"memory"') < events.text.index('"status":"completed"')
        history = client.get("/api/v1/incidents").json()
        assert history["count"] == 1
        assert history["items"][0]["frame_timestamp_ms"] == 500


def test_operator_selected_sensor_scenario_controls_every_generated_frame(
    tmp_path: Path,
) -> None:
    with make_client(
        tmp_path, detector=StubAccidentDetector(), frame_reader=StubFrameReader()
    ) as client:
        authorize(client)
        video = client.post(
            "/api/v1/videos",
            files={"video": ("scenario.mp4", b"video", "video/mp4")},
        ).json()
        job = client.post(
            f"/api/v1/videos/{video['video_id']}/process",
            json={
                "camera_id": "cam-scenario",
                "location": "Selected Map Point",
                "sensor_scenario": "smoke_high",
            },
        ).json()

        completed = client.get(f"/api/v1/processing-jobs/{job['job_id']}").json()
        stream = client.get(f"/api/v1/videos/{video['video_id']}/sensor-stream").json()
        assert completed["sensor_scenario"] == "smoke_high"
        assert stream["scenario"] == "smoke_high"
        for sample in stream["samples"]:
            readings = {item["sensor_type"]: item["probability"] for item in sample["readings"]}
            assert readings["smoke"] >= 0.8
            assert readings["audio"] <= 0.2


def test_video_scan_aggregates_repeated_model_detections_into_one_incident(
    tmp_path: Path,
) -> None:
    class RepeatingDetector:
        def detect(self, frame, *, camera_id: str, location: str):
            confidence = 0.7 if frame.timestamp_ms == 0 else 0.95
            return (DetectorOutput(confidence, 0.9, 1, False, frame.timestamp_ms, location),)

    with make_client(
        tmp_path, detector=RepeatingDetector(), frame_reader=StubFrameReader()
    ) as client:
        authorize(client)
        video = client.post(
            "/api/v1/videos",
            files={"video": ("repeated.mp4", b"video", "video/mp4")},
        ).json()
        job = client.post(
            f"/api/v1/videos/{video['video_id']}/process",
            json={"camera_id": "cam-7", "location": "Airport Road"},
        ).json()
        completed = client.get(f"/api/v1/processing-jobs/{job['job_id']}").json()
        history = client.get("/api/v1/incidents").json()

        assert completed["detections_found"] == 2
        assert history["count"] == 1
        assert history["items"][0]["frame_timestamp_ms"] == 500


def test_video_scan_creates_separate_incidents_for_temporally_distinct_events(
    tmp_path: Path,
) -> None:
    class SeparatedFrameReader:
        def frames(self, path: Path, sample_fps: float):
            frames = [VideoFrame(0, 0, object()), VideoFrame(1, 10_000, object())]
            return len(frames), iter(frames)

    class AlwaysDetects:
        def detect(self, frame, *, camera_id: str, location: str):
            return (DetectorOutput(0.9, 0.9, 1, False, frame.timestamp_ms, location),)

    with make_client(
        tmp_path, detector=AlwaysDetects(), frame_reader=SeparatedFrameReader()
    ) as client:
        authorize(client)
        video = client.post(
            "/api/v1/videos",
            files={"video": ("two-events.mp4", b"video", "video/mp4")},
        ).json()
        job = client.post(
            f"/api/v1/videos/{video['video_id']}/process",
            json={"camera_id": "cam-7", "location": "Airport Road"},
        ).json()
        completed = client.get(f"/api/v1/processing-jobs/{job['job_id']}").json()
        history = client.get("/api/v1/incidents").json()

        assert completed["detections_found"] == 2
        assert history["count"] == 2
        assert {item["frame_timestamp_ms"] for item in history["items"]} == {0, 10_000}


def test_mock_auth_and_onboarding_never_return_raw_api_key(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "organization_name": "Metro Safety Lab",
                "email": "operator@example.com",
                "password": "strong-demo-password",
            },
        )
        assert signup.status_code == 201
        token = signup.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        configured = client.put(
            "/api/v1/onboarding",
            headers=headers,
            json={
                "camera_name": "Junction Camera 7",
                "camera_location": "Airport Road",
                "emergency_contact": "+910000000000",
                "notification_preference": "voice alert for high-severity incidents",
                "agent_api_key": "mock-agent-key-12345678",
            },
        )
        assert configured.status_code == 200
        summary = configured.json()
        assert summary["organization"]["api_key_last_four"] == "5678"
        assert "mock-agent-key" not in configured.text
        assert summary["cameras"][0]["location"] == "Airport Road"

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@example.com", "password": "strong-demo-password"},
        )
        assert login.status_code == 200
        assert login.json()["access_token"] != token


def test_onboarding_requires_authentication(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/api/v1/onboarding").status_code == 401


def test_logout_revokes_session(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.get("/api/v1/incidents").status_code == 401


def test_cancelled_video_job_can_be_retried(tmp_path: Path) -> None:
    with make_client(
        tmp_path, detector=StubAccidentDetector(), frame_reader=StubFrameReader()
    ) as client:
        authorize(client)
        video = client.post(
            "/api/v1/videos",
            files={"video": ("retry.mp4", b"video", "video/mp4")},
        ).json()
        session = client.app.state.onboarding.session_for_token(
            client.headers["Authorization"].split(" ", 1)[1]
        )
        queued = client.app.state.video_processor.create_job(
            video["video_id"], "cam-retry", "Airport Road", session.organization_id
        )
        cancelled = client.post(f"/api/v1/processing-jobs/{queued.job_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        retried = client.post(f"/api/v1/processing-jobs/{queued.job_id}/retry")
        assert retried.status_code == 202
        assert retried.json()["job_id"] != queued.job_id
        assert (
            client.get(f"/api/v1/processing-jobs/{retried.json()['job_id']}").json()["status"]
            == "completed"
        )


def test_operational_resources_are_isolated_by_organization(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        first = client.post(
            "/api/v1/auth/signup",
            json={
                "organization_name": "First Org",
                "email": "first@example.test",
                "password": "first-password",
            },
        ).json()["access_token"]
        second = client.post(
            "/api/v1/auth/signup",
            json={
                "organization_name": "Second Org",
                "email": "second@example.test",
                "password": "second-password",
            },
        ).json()["access_token"]
        first_headers = {"Authorization": f"Bearer {first}"}
        second_headers = {"Authorization": f"Bearer {second}"}

        incident = client.post(
            "/api/v1/incidents/process",
            headers=first_headers,
            json=detection_payload(),
        ).json()
        video = client.post(
            "/api/v1/videos",
            headers=first_headers,
            files={"video": ("private.mp4", b"video", "video/mp4")},
        ).json()

        assert client.get("/api/v1/incidents", headers=second_headers).json()["count"] == 0
        assert (
            client.get(
                f"/api/v1/incidents/{incident['incident_id']}", headers=second_headers
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/videos/{video['video_id']}/content", headers=second_headers
            ).status_code
            == 404
        )


def test_uploaded_policy_is_extracted_and_used_in_reasoning(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        token = client.post(
            "/api/v1/auth/signup",
            json={
                "organization_name": "Policy Org",
                "email": "policy@example.com",
                "password": "policy-password",
            },
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.put(
            "/api/v1/onboarding",
            headers=headers,
            json={
                "camera_name": "Cam 1",
                "camera_location": "Airport Road",
                "emergency_contact": "+91123",
                "agent_api_key": "mock-key-1234",
            },
        )
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        pdf.cell(
            text="Accident emergency Airport Road policy requires medical dispatch immediately."
        )
        uploaded = client.post(
            "/api/v1/knowledge/policies",
            headers=headers,
            files={"policy": ("response-policy.pdf", bytes(pdf.output()), "application/pdf")},
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["chunk_count"] == 1

        incident = client.post(
            "/api/v1/incidents/process",
            headers=headers,
            json={**detection_payload(), "location": "Unrelated Remote Warehouse"},
        ).json()
        retrieval = incident["events"][2]["payload"]
        reasoning = incident["events"][3]["payload"]
        assert retrieval["evidence"][0]["filename"] == "response-policy.pdf"
        assert retrieval["evidence"][0]["score"] > 0
        assert "requires medical dispatch" in reasoning["rationale"][1]

        video = client.post(
            "/api/v1/videos",
            headers=headers,
            files={"video": ("scoped.mp4", b"validation-video", "video/mp4")},
        ).json()
        video_incident = client.post(
            f"/api/v1/videos/{video['video_id']}/detections",
            headers=headers,
            json={
                "camera_id": "cam-1",
                "confidence": 0.94,
                "impact_score": 0.92,
                "vehicle_count": 2,
                "stopped_vehicle": True,
                "frame_timestamp_ms": 500,
                "location": "Airport Road",
            },
        ).json()
        assert video_incident["events"][2]["payload"]["evidence"][0]["filename"] == (
            "response-policy.pdf"
        )


def test_location_search_endpoints_use_configured_map_provider(tmp_path: Path) -> None:
    class StubGeocoder:
        def search(self, query: str):
            return [
                {
                    "display_name": f"{query}, Bengaluru",
                    "latitude": 12.97,
                    "longitude": 77.59,
                    "category": "place",
                }
            ]

        def reverse(self, latitude: float, longitude: float):
            return {
                "display_name": "Selected Junction, Bengaluru",
                "latitude": latitude,
                "longitude": longitude,
                "category": "road",
            }

    with make_client(tmp_path) as client:
        authorize(client)
        client.app.state.geocoder = StubGeocoder()
        search = client.get("/api/v1/locations/search", params={"q": "Airport Road"})
        reverse = client.get(
            "/api/v1/locations/reverse",
            params={"latitude": 12.97, "longitude": 77.59},
        )

        assert search.status_code == 200
        assert search.json()["items"][0]["display_name"] == "Airport Road, Bengaluru"
        assert reverse.status_code == 200
        assert reverse.json()["display_name"] == "Selected Junction, Bengaluru"
