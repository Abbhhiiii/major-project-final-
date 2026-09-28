from pathlib import Path
from types import SimpleNamespace

from packages.surveillance.domain.models import Action
from packages.surveillance.infrastructure.execution import ExecutionRouter, PdfReportRenderer


class RecordingDeliveries:
    def __init__(self) -> None:
        self.items = []

    def save(self, record) -> None:
        self.items.append(record)


class FakeMessages:
    def __init__(self) -> None:
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(sid="SM-test")


class FakeCalls:
    def __init__(self) -> None:
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(sid="CA-test")


def test_twilio_whatsapp_sends_incident_summary_without_public_pdf(tmp_path: Path) -> None:
    deliveries = RecordingDeliveries()
    reports = PdfReportRenderer(tmp_path)
    details = {
        "detection_id": "det-1", "camera_id": "CAM-7", "location": "North Gate",
        "occurred_at": "2026-08-03T10:00:00Z", "severity": "critical", "rationale": ["Policy matched."],
        "policies": ["Escalate verified critical events."],
        "procedures": ["Keep the access route clear."],
    }
    reports.render(Action("pdf_report", "det-1", "Critical risk at North Gate", details))
    router = ExecutionRouter(
        deliveries, reports, twilio_enabled=False, whatsapp_enabled=True,
        whatsapp_from_number="+14155238886",
    )
    messages = FakeMessages()
    router.twilio = SimpleNamespace(messages=messages)

    router.execute(Action("whatsapp_alert", "+91 98765 43210", "Critical risk at North Gate", details))

    assert messages.request["to"] == "whatsapp:+919876543210"
    assert messages.request["from_"] == "whatsapp:+14155238886"
    assert messages.request["body"].startswith("SENTRIX CRITICAL ALERT")
    assert "Critical risk at North Gate" in messages.request["body"]
    assert "Open Sentrix to review the complete evidence" in messages.request["body"]
    assert "media_url" not in messages.request
    assert deliveries.items[0].provider_reference == "SM-test"


class FakeVonage:
    def __init__(self) -> None:
        self.text_request = None
        self.file_request = None

    def send_text(self, recipient: str, text: str) -> str:
        self.text_request = {"recipient": recipient, "text": text}
        return "vonage-text-id"

    def send_file(self, recipient: str, url: str, caption: str) -> str:
        self.file_request = {"recipient": recipient, "url": url, "caption": caption}
        return "vonage-file-id"


def test_vonage_whatsapp_sends_one_dashboard_alert(tmp_path: Path) -> None:
    deliveries = RecordingDeliveries()
    reports = PdfReportRenderer(tmp_path)
    details = {
        "detection_id": "det-vonage", "camera_id": "CAM-9", "location": "East Gate",
        "occurred_at": "2026-09-28T10:00:00Z", "severity": "high",
        "rationale": ["Verified evidence."], "policies": ["Notify the duty officer."],
        "procedures": ["Preserve camera evidence."],
    }
    reports.render(Action("pdf_report", "det-vonage", "High risk at East Gate", details))
    router = ExecutionRouter(
        deliveries,
        reports,
    )
    vonage = FakeVonage()
    router.vonage = vonage

    router.execute(Action("whatsapp_alert", "+91 98765 43210", "High risk at East Gate", details))

    assert vonage.text_request["recipient"] == "+91 98765 43210"
    assert vonage.text_request["text"].startswith("SENTRIX HIGH ALERT")
    assert "High risk at East Gate" in vonage.text_request["text"]
    assert "Open Sentrix to review the complete evidence" in vonage.text_request["text"]
    assert vonage.file_request is None
    assert deliveries.items[0].provider_reference == "vonage-text-id"


def test_voice_uses_groq_message_and_normalized_numbers(tmp_path: Path) -> None:
    deliveries = RecordingDeliveries()
    router = ExecutionRouter(deliveries, PdfReportRenderer(tmp_path), from_number="+1 (555) 123-4567")
    calls = FakeCalls()
    router.twilio = SimpleNamespace(calls=calls)

    router.execute(Action("voice_alert", "+91 98765 43210", "Critical incident at North Gate."))

    assert calls.request["to"] == "+919876543210"
    assert calls.request["from_"] == "+15551234567"
    assert "Critical incident at North Gate." in calls.request["twiml"]
    assert deliveries.items[0].provider_reference == "CA-test"


def test_failed_twilio_attempt_is_recorded(tmp_path: Path) -> None:
    deliveries = RecordingDeliveries()
    router = ExecutionRouter(deliveries, PdfReportRenderer(tmp_path), from_number="+15551234567")
    calls = FakeCalls()
    router.twilio = SimpleNamespace(calls=calls)

    try:
        router.execute(Action("voice_alert", "not-a-phone-number", "Critical incident."))
    except ValueError:
        pass

    assert deliveries.items[0].status == "failed"
    assert deliveries.items[0].provider_reference == "ValueError"


def test_demo_mode_simulates_external_action_without_twilio(tmp_path: Path) -> None:
    deliveries = RecordingDeliveries()
    router = ExecutionRouter(
        deliveries,
        PdfReportRenderer(tmp_path),
        execution_mode="simulate",
    )

    router.execute(Action("voice_alert", "+919876543210", "Critical incident at North Gate."))

    assert deliveries.items[0].status == "simulated"
    assert deliveries.items[0].provider_reference == "demo-simulation"
    assert router.twilio is None
