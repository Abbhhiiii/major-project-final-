"""Validate Sentrix Twilio configuration without sending a call or message."""

from __future__ import annotations

import re

from twilio.base.exceptions import TwilioException
from twilio.rest import Client

from packages.surveillance.infrastructure.config import Settings


def is_e164(value: str) -> bool:
    return bool(re.fullmatch(r"\+[1-9]\d{7,14}", re.sub(r"[\s().-]", "", value)))


def main() -> int:
    settings = Settings()
    checks = {
        "Twilio enabled": settings.twilio_enabled,
        "Account SID": bool(settings.twilio_account_sid),
        "API credentials": bool(
            settings.twilio_auth_token
            or (settings.twilio_api_key_sid and settings.twilio_api_key_secret)
        ),
        "Voice sender is E.164": is_e164(settings.twilio_from_number),
        "WhatsApp enabled": settings.twilio_whatsapp_enabled,
        "WhatsApp sender is E.164": is_e164(settings.twilio_whatsapp_from_number),
        "Public HTTPS report URL": settings.public_base_url.startswith("https://"),
        "Report signing secret": len(settings.report_link_secret) >= 32,
    }
    for label, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}  {label}")

    if not checks["Account SID"] or not checks["API credentials"]:
        return 1
    try:
        if settings.twilio_api_key_sid and settings.twilio_api_key_secret:
            client = Client(
                settings.twilio_api_key_sid,
                settings.twilio_api_key_secret,
                settings.twilio_account_sid,
            )
        else:
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.list(limit=1)
    except TwilioException as error:
        print(f"FAIL  Twilio authentication ({type(error).__name__})")
        return 1
    print("PASS  Twilio authentication")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
