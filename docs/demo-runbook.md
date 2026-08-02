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

## Known deferred integration

Twilio remains disabled until a Twilio-owned voice-capable sender number is available and a real call passes validation.
