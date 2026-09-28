# Per-footage sensor metadata cases

Upload a CCTV video in Sentrix, attach one JSON file from this folder, and then start the scan.
The metadata belongs to that uploaded video ID and supplies synthetic smoke/audio readings because
physical sensors are unavailable for the demo.

| File | Expected fusion behavior |
| --- | --- |
| `01_high_smoke_and_audio.json` | Both sensors corroborate the visual candidate and add an agreement bonus. |
| `02_very_high_smoke_override.json` | Fresh reliable smoke crosses the guarded override threshold. |
| `03_very_high_audio_override.json` | Fresh reliable audio crosses the guarded override threshold. |
| `04_low_smoke_and_audio.json` | Two reliable low readings can apply the contradiction penalty to strong visual evidence. |
| `05_stale_high_signals_no_override.json` | High raw readings decay through freshness and must not trigger an override. |

These are deterministic synthetic inputs for demonstrating software behavior. They are not real
measurements and must not be presented as evidence of production sensor accuracy.
