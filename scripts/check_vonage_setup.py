"""Validate the Vonage sandbox configuration and optionally send one real test message."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.surveillance.infrastructure.config import Settings
from packages.surveillance.infrastructure.execution import VonageWhatsAppClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="send one real WhatsApp message")
    parser.add_argument("--to", help="allow-listed WhatsApp number in international format")
    args = parser.parse_args()
    settings = Settings()
    required = {
        "SURVEILLANCE_VONAGE_API_KEY": settings.vonage_api_key,
        "SURVEILLANCE_VONAGE_API_SECRET": settings.vonage_api_secret,
        "SURVEILLANCE_VONAGE_WHATSAPP_FROM_NUMBER": settings.vonage_whatsapp_from_number,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print("Missing Vonage settings: " + ", ".join(missing))
        return 1
    print("Vonage sandbox credentials are configured locally.")
    if not args.send:
        print("No message sent. Add --send --to <number> for an explicit live test.")
        return 0
    if not args.to:
        parser.error("--to is required with --send")
    client = VonageWhatsAppClient(
        settings.vonage_api_key,
        settings.vonage_api_secret,
        settings.vonage_whatsapp_from_number,
        settings.vonage_messages_url,
    )
    reference = client.send_text(
        args.to,
        "Sentrix connectivity check: the Vonage WhatsApp sandbox is connected.",
    )
    print(f"Vonage accepted the message. Reference: {reference}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
