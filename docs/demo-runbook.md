# Demo runbook

## Start

```bash
scripts/run_demo.sh
```

Open `http://127.0.0.1:5173`, sign in, upload the mock policy, upload a positive test MP4, and start the scan.

## Expected sequence

1. The complete video reaches 100% model scan progress.
2. Detection and forced verification appear.
3. Uploaded policy evidence appears in retrieval.
4. Groq decision, planning, execution, and memory appear.
5. The incident table provides **Details** and **PDF** actions.
6. Details show the durable provider/model, reasoning, evidence, plan, and delivery statuses.

## Accuracy evaluation

```bash
.venv/bin/python -m scripts.evaluate_accident_model demo_assets/test_videos/evaluation-manifest.csv
```

## Recoverable reset

Stop the running application first, then run:

```bash
scripts/backup_and_reset_demo.sh --confirm
```

The command moves the database, uploads, policies, and reports into `.demo-backups/<timestamp>` instead of deleting them.

## Live Twilio activation

1. Rotate any credential previously shared in chat, then create a Standard API key under the same
   Twilio Account SID. Store only the new SID and secret in `.env`.
2. Claim/buy a voice-capable Twilio number (or configure a verified outgoing caller ID) and set it as
   `SURVEILLANCE_TWILIO_FROM_NUMBER`. Trial accounts must also verify the destination number and
   enable the destination country under Voice geographic permissions.
3. Activate the WhatsApp testing environment, join it from the demo phone, and send a fresh inbound
   message immediately before the demo to open the 24-hour free-form media window.
4. Set the WhatsApp test sender, expose port 8000 through a public HTTPS tunnel, set that origin as
   `SURVEILLANCE_PUBLIC_BASE_URL`, and generate a long random `SURVEILLANCE_REPORT_LINK_SECRET`.
5. Enable both Twilio flags, run `.venv/bin/python -m scripts.check_twilio_setup`, then perform one
   controlled call case and one controlled message case. Only after both reach the phone should the
   corresponding `*_LIVE_VALIDATED` flags be set to `true`.

The message branch sends Groq's incident text, retrieved policy procedures, and the generated PDF.
The call branch speaks Groq's incident text and guarantees that the camera location is included.
