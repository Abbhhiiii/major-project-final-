from html import escape
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from twilio.rest import Client

from ..domain.models import Action, DeliveryRecord
from ..ports import DeliveryRepository


class PdfReportRenderer:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def render(self, action: Action) -> Path:
        detection_id = str(action.details["detection_id"])
        path = self.root / f"incident-{detection_id}.pdf"
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Sentinel AI Incident Report", styles["Title"]),
            Spacer(1, 16),
            Paragraph(action.message, styles["Heading2"]),
        ]
        for label, key in (
            ("Detection ID", "detection_id"),
            ("Camera", "camera_id"),
            ("Location", "location"),
            ("Occurred at", "occurred_at"),
            ("Severity", "severity"),
        ):
            story.append(Paragraph(f"<b>{label}:</b> {escape(str(action.details[key]))}", styles["BodyText"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Agent rationale", styles["Heading2"]))
        for item in action.details.get("rationale", []):
            story.append(Paragraph(f"• {escape(str(item))}", styles["BodyText"]))
        SimpleDocTemplate(str(path), pagesize=A4, title="Sentinel AI Incident Report").build(story)
        return path


class ExecutionRouter:
    def __init__(
        self,
        deliveries: DeliveryRepository,
        reports: PdfReportRenderer,
        *,
        twilio_enabled: bool = False,
        account_sid: str = "",
        auth_token: str = "",
        api_key_sid: str = "",
        api_key_secret: str = "",
        from_number: str = "",
    ) -> None:
        self.deliveries = deliveries
        self.reports = reports
        self.twilio_enabled = twilio_enabled
        self.from_number = from_number
        if twilio_enabled and api_key_sid and api_key_secret and account_sid:
            self.twilio = Client(api_key_sid, api_key_secret, account_sid)
        elif twilio_enabled and account_sid and auth_token:
            self.twilio = Client(account_sid, auth_token)
        else:
            self.twilio = None

    def execute(self, action: Action) -> None:
        detection_id = str(action.details.get("detection_id", ""))
        reference = ""
        report_path = ""
        status = "delivered"
        if action.kind == "pdf_report":
            report_path = str(self.reports.render(action))
        elif action.kind == "voice_alert":
            if self.twilio is None:
                raise RuntimeError("Twilio voice execution is not configured")
            call = self.twilio.calls.create(
                to=action.target,
                from_=self.from_number,
                twiml=f"<Response><Say>{escape(action.message)}</Say></Response>",
            )
            reference = call.sid
        self.deliveries.save(
            DeliveryRecord(
                detection_id=detection_id,
                action_kind=action.kind,
                target=action.target,
                status=status,
                message=action.message,
                provider_reference=reference,
                report_path=report_path,
            )
        )
