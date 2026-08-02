# Airport Road Multi-Constraint Accident Response Policy

Policy ID: ARP-2026-04. This policy applies to Airport Road cameras and connected Bengaluru junctions.

## Verification boundary

Only events accepted by the false-alarm verification gate may proceed. The reasoning agent must use detector confidence, impact score, vehicle count, stopped-vehicle state, location, retrieved history, contacts, and organization preferences. It must never invent injuries, fire, hazardous cargo, blocked lanes, identities, phone numbers, or emergency delivery outcomes.

## Severity matrix

- Critical: impact score at least 0.90; or impact at least 0.80 with three or more vehicles; or a verified high-impact event at Airport Road with repeated prior incidents.
- High: impact score from 0.75 through 0.89; or confidence at least 0.85 combined with a stopped vehicle; or two or more vehicles with impact at least 0.70.
- Medium: verified event below the high threshold that still shows collision evidence.
- Low: incomplete or weak evidence requiring operator review. A forced verification acceptance does not authorize invented evidence.

When multiple rules apply, use the highest supported severity and name the exact rule in the rationale.

## Airport Road constraints

Airport Road is a priority corridor. High and critical incidents require an immediate operations-dashboard alert. The alert must include severity, camera, Airport Road location, observed vehicle count, and that the event was model detected and verification accepted. If prior incidents are retrieved for the location, mention the count in reasoning and prioritize operator review. Do not state that traffic is blocked unless the evidence explicitly says so.

## Action constraints

Every verified event requires a dashboard alert, PDF report, and durable incident/audit memory. High and critical incidents may recommend emergency escalation only when a retrieved emergency contact exists. Voice execution is permitted only when Twilio is enabled, a Twilio-owned voice-capable sender is configured, and the channel has passed live validation. Until then, plan dashboard and PDF actions only; never claim that a call was placed or delivered.

Medium incidents remain dashboard-first unless retrieved procedures explicitly require escalation. Low incidents request operator review and do not contact emergency services.

## Message and audit requirements

Messages must be concise and factual. The Groq decision must identify which policy threshold caused the severity, cite retrieved policy evidence, explain contact availability, and distinguish recommended escalation from completed execution. Reports must contain detection ID, camera, location, timestamp, severity, rationale, planned actions, successful actions, and failures. Failed actions must remain visible and must not be rewritten as successful.

## Conflict resolution

Safety constraints override notification preferences. Retrieved organization preferences may choose among allowed channels but cannot enable an unvalidated provider. More specific Airport Road rules override general procedures. When evidence is insufficient or policies conflict, choose the safer supported dashboard action and request operator review rather than fabricating certainty.
