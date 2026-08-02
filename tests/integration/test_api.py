from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from fpdf import FPDF

from apps.backend.main import create_app
from packages.surveillance.agents import ReasoningAgent
from packages.surveillance.infrastructure.config import Settings
from packages.surveillance.perception.models import DetectorOutput, VideoFrame


class StubFrameReader:
    def frames(self, path: Path, sample_fps: float) -> tuple[int, Iterator[VideoFrame]]:
        frames = [VideoFrame(0, 0, object()), VideoFrame(10, 500, object())]
        return len(frames), iter(frames)


class StubAccidentDetector:
    def detect(
        self, frame: VideoFrame, *, camera_id: str, location: str
    ) -> tuple[DetectorOutput, ...]:
        if frame.timestamp_ms != 500:
            return ()
        return (DetectorOutput(0.95, 0.91, 2, True, frame.timestamp_ms, location),)


def make_client(
    tmp_path: Path, *, detector: Any = None, frame_reader: Any = None
) -> TestClient:
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

        analytics = client.get("/api/v1/analytics/summary").json()
        assert analytics == {"total_incidents": 1, "by_severity": {"critical": 1}}

        deliveries = client.get(f"/api/v1/incidents/{incident_id}/deliveries").json()
        assert deliveries["count"] == 2
        report_record = next(item for item in deliveries["items"] if item["action_kind"] == "pdf_report")
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


def test_missing_incident_returns_not_found(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        authorize(client)
        response = client.get("/api/v1/incidents/not-a-real-id")
        assert response.status_code == 404


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
        assert events.text.count("event: pipeline") == 7
        assert '"stage":"reasoning"' in events.text
        assert events.text.index('"stage":"memory"') < events.text.index(
            '"status":"completed"'
        )
        history = client.get("/api/v1/incidents").json()
        assert history["count"] == 1
        assert history["items"][0]["frame_timestamp_ms"] == 500


def test_video_scan_aggregates_repeated_model_detections_into_one_incident(
    tmp_path: Path,
) -> None:
    class RepeatingDetector:
        def detect(self, frame, *, camera_id: str, location: str):
            confidence = 0.7 if frame.timestamp_ms == 0 else 0.95
            return (
                DetectorOutput(
                    confidence, 0.9, 1, False, frame.timestamp_ms, location
                ),
            )

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
        assert client.get(
            f"/api/v1/processing-jobs/{retried.json()['job_id']}"
        ).json()["status"] == "completed"


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
        assert client.get(
            f"/api/v1/incidents/{incident['incident_id']}", headers=second_headers
        ).status_code == 404
        assert client.get(
            f"/api/v1/videos/{video['video_id']}/content", headers=second_headers
        ).status_code == 404


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
        pdf.cell(text="Accident emergency Airport Road policy requires medical dispatch immediately.")
        uploaded = client.post(
            "/api/v1/knowledge/policies",
            headers=headers,
            files={"policy": ("response-policy.pdf", bytes(pdf.output()), "application/pdf")},
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["chunk_count"] == 1

        incident = client.post(
            "/api/v1/incidents/process", headers=headers, json=detection_payload()
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
