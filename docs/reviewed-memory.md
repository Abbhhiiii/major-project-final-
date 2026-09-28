# Reviewed incident memory

After verification, policy retrieval also retrieves up to five reviewed cases from the same
organization and location. The system stores original scanning and verification snapshots in
the incident audit; operator corrections are stored separately in the incident_reviews table.
History → Details → Review this incident accepts severity, response, false-alarm status and reason.
Saving a review replaces the current correction for that incident; the original AI audit is retained.

Matches require identical available sensor types and a weighted full-evidence similarity of at least
0.70. The comparison includes CV confidence, visual impact, selected-frame sensor probability,
reliability and freshness, plus the per-frame sensor timeline's mean, maximum and variability.
Each feature match is `1 - normalized absolute distance`, clipped to `[0, 1]`; overall similarity is
the sum of feature match multiplied by feature weight. This is a transparent retrieval metric, not a
trained prediction model. Legacy incidents without scan snapshots are excluded. Different locations
and organizations are excluded. Missing sensors do not match measured zero readings.

Groq receives these reviewed examples inside `policy_retrieval.reviewed_incidents` together with
the current scan, current verification and policy evidence. It creates a current-evidence draft and
explains the comparison. The closest valid human review is then reconciled with that draft using:

```text
blended ordinal rank = round_half_up((1 - similarity) × current draft rank
                                     + similarity × reviewed rank)
upward severity floor = floor(similarity × reviewed severity rank)
```

Severity uses `low=0` through `critical=3`; action uses `none=0`, `message=1`, `call=2`. Consequently,
a 100% match reproduces the human-reviewed severity/action exactly, while a lower match has exactly
its similarity as influence and leaves the complement to current evidence. For upward corrections,
the similarity-derived floor prevents a strong reviewed incident from collapsing to low; a roughly
80%-similar reviewed `HIGH` incident has at least a `MEDIUM` severity floor. False-alarm reviews
target `low/none`. The strongest retrieved match is used so weaker incidents cannot dilute an exact
match. All source ranks, weights, continuous scores, and the final result are stored in the audit and
shown in Decision Reconstruction.

Threshold learning is persistent but separate from action reconciliation. Each organization/location
stores a learned baseline and a list of incorporated `incident_id@reviewed_at` versions. A new review
can move the bounded threshold once; the resulting threshold becomes the next scan's baseline. The
same unchanged review is displayed as already learned and cannot repeatedly push the threshold.

The structured response_action selects call, message or none. Call plans a voice alert; message
plans WhatsApp; none records the incident/report only. Unverified or contactless escalation is
rejected at the reasoning boundary. Local review/retrieval tests do not prove live Groq behavior
or real Twilio delivery. A separate bounded adaptive-threshold model applies recency-weighted human
corrections within the hard 0.60–0.76 safety range. Twilio remains separately configurable.
