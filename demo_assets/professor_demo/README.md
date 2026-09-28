# Sentrix professor demonstration

Each numbered MP4 has a matching JSON file. Keep the filenames unchanged.
Sensor readings are synthetic probability fixtures; the videos are reused short model-test clips, including still-image scenes and neutral backgrounds. Audio metadata is not extracted from an audio track. These are controlled software demonstrations, not sensor accuracy benchmarks.

## Run

1. Restart the backend after generating this pack: sensor metadata is read at startup.
2. Open the dashboard, sign in, and upload your policy PDF.
3. Upload one numbered MP4, enter a location, and click Scan uploaded footage.
4. Inspect the candidate sources, verification evidence, and AI response. No-candidate cases produce no new decision.
5. Keep Twilio/WhatsApp disabled while rehearsing. Groq needs a configured key. Its final severity and actions depend on the policy and contact configuration.

The server automatically finds synthetic sensors by original filename in demo_assets/test_videos/sensor-metadata.json. The paired JSON files are for inspection; the UI does not upload them. The combined catalog here can also be selected via SURVEILLANCE_SENSOR_METADATA_PATH.

## Verified results

| Video | Candidate sources | Verification | Fused score | Override |
|---|---|---|---|---|
| 01_all_sources_agree.mp4 | visual, smoke, audio | verified | 0.9803 | none |
| 02_smoke_only_override.mp4 | smoke | verified | 0.9 | smoke |
| 03_audio_only_override.mp4 | audio | verified | 0.9 | audio |
| 04_borderline_visual_corroborated.mp4 | visual, smoke, audio | verified | 0.9115 | none |
| 05_visual_contradicted.mp4 | visual | suppressed | 0.1423 | none |
| 06_stale_sensor_spike.mp4 | none | no_candidate | — | — |
| 07_unreliable_sensor_spike.mp4 | none | no_candidate | — | — |
| 08_missing_sensors_visual_only.mp4 | visual | verified | 0.8067 | none |
| 09_normal_scene.mp4 | none | no_candidate | — | — |
| 10_sensor_candidate_rejected.mp4 | smoke | suppressed | 0.0307 | none |
| 11_borderline_visual_only.mp4 | visual | suppressed | 0.5693 | none |

Compare 04 and 11: identical footage with versus without sensor support. Compare 01, 05, and 08: identical footage with agreement, contradiction, or missing auxiliary data.

Case 05 is a hypothetical contradiction test, not proof that the accident footage is a false alarm. Absence of smoke or audio does not generally rule out an incident; production coefficients need real-data calibration.

validation-results.json records actual CV/fusion results, without calling Groq or external notification services. Rebuild with `.venv/bin/python -m scripts.build_professor_demo`.
