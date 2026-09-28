import base64
import json
import re
import ssl
from html import escape
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import certifi
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from twilio.rest import Client

from ..domain.models import Action, DeliveryRecord
from ..ports import DeliveryRepository


class VonageWhatsAppClient:
    """Infrastructure adapter for the Vonage Messages Sandbox WhatsApp channel."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        sender: str,
        messages_url: str = "https://messages-sandbox.nexmo.com/v1/messages",
        timeout_seconds: float = 15,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.sender = self._digits(sender)
        self.messages_url = messages_url
        self.timeout_seconds = timeout_seconds

    def send_text(self, recipient: str, text: str) -> str:
        return self._post(
            {
                "to": self._digits(recipient),
                "from": self.sender,
                "channel": "whatsapp",
                "message_type": "text",
                "text": text,
            }
        )

    def send_file(self, recipient: str, url: str, caption: str) -> str:
        return self._post(
            {
                "to": self._digits(recipient),
                "from": self.sender,
                "channel": "whatsapp",
                "message_type": "file",
                "file": {"url": url, "caption": caption},
            }
        )

    def _post(self, payload: dict[str, object]) -> str:
        credentials = base64.b64encode(
            f"{self.api_key}:{self.api_secret}".encode()
        ).decode()
        request = Request(
            self.messages_url,
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urlopen(
                request,
                timeout=self.timeout_seconds,
                context=ssl_context,
            ) as response:
                result = json.loads(response.read().decode() or "{}")
        except HTTPError as error:
            response_body = error.read().decode(errors="replace")[:500]
            raise RuntimeError(
                f"Vonage WhatsApp request failed with HTTP {error.code}: {response_body}"
            ) from error
        message_id = str(result.get("message_uuid") or result.get("message_id") or "")
        if not message_id:
            raise RuntimeError("Vonage WhatsApp response did not include a message identifier")
        return message_id

    @staticmethod
    def _digits(number: str) -> str:
        normalized = re.sub(r"[\s+().-]", "", number)
        if not re.fullmatch(r"[1-9]\d{7,14}", normalized):
            raise ValueError("Vonage WhatsApp numbers must use international digits without '+'")
        return normalized


class PdfReportRenderer:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def render(self, action: Action) -> Path:
        detection_id = str(action.details["detection_id"])
        path = self.root / f"incident-{detection_id}.pdf"
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Sentrix Incident Report", styles["Title"]),
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
        for title, key in (("Retrieved policy", "policies"), ("Response procedures", "procedures")):
            values = action.details.get(key, [])
            if values:
                story.append(Spacer(1, 12))
                story.append(Paragraph(title, styles["Heading2"]))
                for item in values:
                    story.append(Paragraph(f"• {escape(str(item))}", styles["BodyText"]))
        SimpleDocTemplate(str(path), pagesize=A4, title="Sentrix Incident Report").build(story)
        return path

    def path_for(self, detection_id: str) -> Path:
        return self.root / f"incident-{detection_id}.pdf"


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
        whatsapp_enabled: bool = False,
        whatsapp_from_number: str = "",
        vonage_whatsapp_enabled: bool = False,
        vonage_api_key: str = "",
        vonage_api_secret: str = "",
        vonage_whatsapp_from_number: str = "",
        vonage_messages_url: str = "https://messages-sandbox.nexmo.com/v1/messages",
        public_base_url: str = "",
        report_link_secret: str = "",
        execution_mode: str = "live",
    ) -> None:
        self.deliveries = deliveries
        self.reports = reports
        self.twilio_enabled = twilio_enabled
        self.from_number = from_number
        self.whatsapp_enabled = whatsapp_enabled
        self.whatsapp_from_number = whatsapp_from_number
        self.public_base_url = public_base_url.rstrip("/")
        self.report_link_secret = report_link_secret
        self.execution_mode = execution_mode
        if twilio_enabled and api_key_sid and api_key_secret and account_sid:
            self.twilio = Client(api_key_sid, api_key_secret, account_sid)
        elif twilio_enabled and account_sid and auth_token:
            self.twilio = Client(account_sid, auth_token)
        else:
            self.twilio = None
        if (
            vonage_whatsapp_enabled
            and vonage_api_key
            and vonage_api_secret
            and vonage_whatsapp_from_number
        ):
            self.vonage = VonageWhatsAppClient(
                vonage_api_key,
                vonage_api_secret,
                vonage_whatsapp_from_number,
                vonage_messages_url,
            )
        else:
            self.vonage = None

    def execute(self, action: Action) -> None:
        detection_id = str(action.details.get("detection_id", ""))
        reference = ""
        report_path = ""
        status = "delivered"
        try:
            if action.kind == "pdf_report":
                report_path = str(self.reports.render(action))
            elif action.kind in {"voice_alert", "whatsapp_alert"} and self.execution_mode == "simulate":
                status = "simulated"
                reference = "demo-simulation"
                if action.kind == "whatsapp_alert":
                    existing_report = self.reports.path_for(detection_id)
                    report_path = str(existing_report) if existing_report.is_file() else ""
            elif action.kind == "voice_alert":
                if self.twilio is None or not self.from_number:
                    raise RuntimeError("Twilio voice execution is not configured")
                call = self.twilio.calls.create(
                    to=self._e164(action.target),
                    from_=self._e164(self.from_number),
                    twiml=f"<Response><Say>{escape(action.message)}</Say></Response>",
                )
                reference = call.sid
            elif action.kind == "whatsapp_alert":
                existing_report = self.reports.path_for(detection_id)
                report_path = str(existing_report) if existing_report.is_file() else ""
                procedures = [str(item) for item in action.details.get("procedures", [])]
                severity = str(action.details.get("severity", "alert")).upper()
                camera = str(action.details.get("camera_id", "unknown camera"))
                location = str(action.details.get("location", "unknown location"))
                occurred_at = str(action.details.get("occurred_at", "time unavailable"))
                body = (
                    f"SENTRIX {severity} ALERT\n\n"
                    f"{action.message}\n\n"
                    f"Camera: {camera}\n"
                    f"Location: {location}\n"
                    f"Time: {occurred_at}"
                )
                if procedures:
                    body += "\n\nPolicy-guided next steps:\n" + "\n".join(
                        f"• {item}" for item in procedures[:4]
                    )
                body += "\n\nOpen Sentrix to review the complete evidence and incident report."
                if self.vonage is not None:
                    reference = self.vonage.send_text(action.target, body[:1500])
                elif self.twilio is not None and self.whatsapp_enabled and self.whatsapp_from_number:
                    message = self.twilio.messages.create(
                        to=f"whatsapp:{self._e164(action.target)}",
                        from_=f"whatsapp:{self._e164(self.whatsapp_from_number)}",
                        body=body[:1500],
                    )
                    reference = message.sid
                else:
                    raise RuntimeError("Vonage or Twilio WhatsApp execution is not configured")
        except Exception as error:
            self.deliveries.save(
                DeliveryRecord(
                    detection_id=detection_id,
                    action_kind=action.kind,
                    target=action.target,
                    status="failed",
                    message=action.message,
                    provider_reference=str(getattr(error, "code", "") or type(error).__name__)[:100],
                    report_path=report_path,
                )
            )
            raise
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

    @staticmethod
    def _e164(number: str) -> str:
        normalized = re.sub(r"[\s().-]", "", number)
        if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
            raise ValueError("Emergency contact must use E.164 format, for example +919876543210")
        return normalized
