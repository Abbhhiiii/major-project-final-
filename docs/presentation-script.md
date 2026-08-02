# Final demonstration script

1. Sign in and explain that all operational data is isolated by organization and sessions expire after twelve hours.
2. Upload `demo_assets/mock-accident-response-policy.pdf`. Point out the severity matrix, Airport Road priority rule, contact constraint, and prohibition on unvalidated voice calls.
3. Upload `demo_assets/test_videos/image2-accident-test.mp4` and start the scan.
4. Explain that the complete video is scanned by the real YOLO checkpoint before reasoning begins.
5. Show detection aggregation, forced false-alarm acceptance, retrieved PDF evidence, live Groq rationale, planning, execution, and memory.
6. Open **History & Analytics**. Show severity distribution, seven-day activity, and organization-scoped history.
7. Open **Details** for the new incident. Show the persisted Groq model, policy excerpt, rationale, planned actions, delivery statuses, and PDF report.
8. Run or show `docs/evaluation-report.md`. State the limitations of the small functional set and do not call its score general accuracy.
9. Explain that Twilio is intentionally deferred until a Twilio-owned voice-capable sender passes a real call validation; the system never reports an offline simulation as delivery.

## Backup path

If external Groq connectivity fails, show the most recent persisted audit and PDF rather than claiming a new live response. Do not substitute deterministic reasoning in production.
