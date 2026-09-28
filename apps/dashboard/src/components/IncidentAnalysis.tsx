import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'

import { downloadIncidentReport, getIncidentAudit, getIncidentDeliveries } from '../api'
import type { AgentAudit, DeliveryRecord, Incident, Severity } from '../types'
import { effectiveReliability, visualProbability } from '../utils/incidentMath'
import { IncidentReview } from './IncidentReview'

const clamp = (value: number) => Math.max(0, Math.min(1, value))
const percent = (value: number) => `${Math.round(clamp(value) * 100)}%`

export function IncidentAnalysis({ incidents }: { incidents: Incident[] }) {
  const [selectedId, setSelectedId] = useState('')
  const effectiveSelectedId = incidents.some(item => item.incident_id === selectedId) ? selectedId : incidents[0]?.incident_id ?? ''
  const [result, setResult] = useState<{ id: string; audit: AgentAudit; deliveries: DeliveryRecord[] } | null>(null)
  const [errorId, setErrorId] = useState('')
  const incident = incidents.find(item => item.incident_id === effectiveSelectedId) ?? null

  useEffect(() => {
    if (!effectiveSelectedId) return
    let active = true
    Promise.all([getIncidentAudit(effectiveSelectedId), getIncidentDeliveries(effectiveSelectedId)])
      .then(([audit, deliveries]) => { if (active) { setResult({ id: effectiveSelectedId, audit, deliveries }); setErrorId('') } })
      .catch(() => { if (active) setErrorId(effectiveSelectedId) })
    return () => { active = false }
  }, [effectiveSelectedId])

  return <section className="incident-analysis immersive-analysis">
    <header className="analysis-hero">
      <div className="analysis-hero-copy"><p className="eyebrow">Incident evidence laboratory</p><h1>Decision reconstruction</h1><p>Replay the evidence, mathematics, retrieved intelligence, and agent action behind any incident.</p></div>
      <label className="incident-picker">Incident record<select value={effectiveSelectedId} onChange={event => setSelectedId(event.target.value)} disabled={!incidents.length}>
        {!incidents.length && <option value="">No incidents recorded</option>}
        {incidents.map(item => <option value={item.incident_id} key={item.incident_id}>{new Date(item.stored_at).toLocaleString()} · {item.location} · {item.severity.toUpperCase()} · #{item.incident_id.slice(0, 8)}</option>)}
      </select></label>
    </header>
    {!incidents.length && <div className="analysis-empty">Run a new scan. Its CV, sensor, fusion, RAG, Groq, and execution evidence will appear here.</div>}
    {effectiveSelectedId && result?.id !== effectiveSelectedId && errorId !== effectiveSelectedId && <div className="analysis-empty">Loading the complete audit trail…</div>}
    {errorId === effectiveSelectedId && <div className="analysis-empty text-red-400">This incident does not contain a readable audit trail.</div>}
    {incident && result?.id === effectiveSelectedId && <IncidentVisualization incident={incident} audit={result.audit} deliveries={result.deliveries} />}
  </section>
}

function IncidentVisualization({ incident, audit, deliveries }: { incident: Incident; audit: AgentAudit; deliveries: DeliveryRecord[] }) {
  const scan = audit.retrieval.scan_snapshot
  const verification = audit.retrieval.verification_snapshot
  const sensors = scan?.sensor_readings ?? []
  const visual = visualProbability(scan?.confidence ?? 0, scan?.impact_score ?? 0)
  const fused = verification?.fused_probability ?? verification?.score ?? 0
  const threshold = verification?.decision_threshold ?? .68
  const forcedAccept = verification?.evidence?.some(item => item.includes('forced accepted')) ?? false
  const contributions = useMemo(() => Object.entries(verification?.contributions ?? {}), [verification])
  const logOdds = contributions.reduce((sum, [, value]) => sum + value, 0)
  const logistic = 1 / (1 + Math.exp(-logOdds))
  const maxContribution = Math.max(1, ...contributions.map(([, value]) => Math.abs(value)))
  const successes = audit.execution.successful_actions ?? []
  const failures = audit.execution.failed_actions ?? []
  const reviews = audit.retrieval.reviewed_incidents ?? []
  const memoryInfluence = audit.decision.memory_influence
  const responseAction = audit.decision.response_action ?? 'none'
  const sourceValues = [
    { label: 'CV confidence', value: scan?.confidence ?? 0, note: 'Detector certainty' },
    { label: 'Visual impact', value: scan?.impact_score ?? 0, note: 'Scene intensity' },
    { label: 'Visual composite', value: visual, note: 'Weighted 65 / 35' },
    ...sensors.map(sensor => ({ label: `${sensor.sensor_type} signal`, value: sensor.probability, note: `${percent(effectiveReliability(sensor.reliability, sensor.age_ms))} effective reliability` })),
  ]

  return <div className="analysis-body">
    <div className="incident-context-strip">
      <div><span>Incident</span><strong>#{incident.incident_id.slice(0, 8)}</strong></div><div><span>Camera location</span><strong>{incident.location}</strong></div><div><span>Captured</span><strong>{new Date(incident.stored_at).toLocaleString()}</strong></div><div><span>Frame</span><strong>{incident.frame_timestamp_ms == null ? 'Direct event' : `${(incident.frame_timestamp_ms / 1000).toFixed(2)}s`}</strong></div>
    </div>

    <section className="risk-cockpit analysis-stage">
      <StageHeading number="01" eyebrow="Risk cockpit" title="How strong was the evidence?" />
      <div className="risk-dial-grid"><RiskDial label="CV confidence" value={scan?.confidence ?? 0} caption="Object detector certainty" /><RiskDial label="Visual impact" value={scan?.impact_score ?? 0} caption="Observed collision intensity" /><RiskDial label="Fused risk" value={fused} caption={`${forcedAccept ? 'Demo gate accepted' : verification?.verified ? 'Verified' : 'Suppressed'} · threshold ${percent(threshold)}`} emphasized /></div>
      <div className="source-comparison" aria-label="Evidence source comparison chart">{sourceValues.map(source => <div className="source-bar-row" key={source.label}><div><strong>{source.label}</strong><small>{source.note}</small></div><div className="source-bar-track"><i style={{ width: percent(source.value) }} /><b style={{ left: percent(threshold) }} /></div><span>{percent(source.value)}</span></div>)}<div className="source-threshold-key"><i /> Verification threshold {percent(threshold)}</div></div>
    </section>

    <section className="analysis-stage">
      <StageHeading number="02" eyebrow="Visual + sensors" title="What entered the fusion model?" />
      <div className="evidence-split">
        <div className="equation-visual"><p>Visual probability</p><div><span>0.65 × {(scan?.confidence ?? 0).toFixed(3)}</span><b>+</b><span>0.35 × {(scan?.impact_score ?? 0).toFixed(3)}</span></div><strong>{visual.toFixed(4)}</strong><small>Confidence contributes {(0.65 * (scan?.confidence ?? 0)).toFixed(3)} · impact contributes {(0.35 * (scan?.impact_score ?? 0)).toFixed(3)}</small></div>
        <div className="scene-constellation"><div className="scene-center"><strong>{scan?.vehicle_count ?? 0}</strong><span>vehicles</span></div><div className="scene-orbit orbit-one">{scan?.stopped_vehicle ? 'Stopped vehicle' : 'Moving scene'}</div><div className="scene-orbit orbit-two">{(scan?.candidate_sources ?? []).join(' + ') || 'visual'}</div><div className="scene-orbit orbit-three">{sensors.length} sensors</div></div>
      </div>
      <div className="sensor-quality-grid">{sensors.map(sensor => { const reliability = effectiveReliability(sensor.reliability, sensor.age_ms); return <article key={`${sensor.sensor_type}-${sensor.source}`}><header><div><span>{sensor.sensor_type}</span><small>{sensor.source}</small></div><strong>{percent(sensor.probability)}</strong></header><div className="sensor-quality-bars"><QualityBar label="Probability" value={sensor.probability} /><QualityBar label="Raw reliability" value={sensor.reliability} /><QualityBar label="Effective reliability" value={reliability} /></div><code>{sensor.reliability.toFixed(3)} × e<sup>−ln2 × {sensor.age_ms}/10000</sup> = {reliability.toFixed(3)}</code></article> })}{!sensors.length && <div className="missing-sensors">No auxiliary readings were present. Missing sensors add zero evidence and are never treated as negative evidence.</div>}</div>
      <SensorTimelineVisualization timeline={scan?.sensor_timeline ?? []} candidateTimestamp={scan?.frame_timestamp_ms ?? null} scenario={scan?.sensor_scenario ?? ''} />
    </section>

    <section className="analysis-stage fusion-stage">
      <StageHeading number="03" eyebrow="Statistical verification" title="How did the probability change?" />
      <AdaptiveThresholdVisualization verification={verification} fused={fused} />
      <ProbabilityJourney contributions={contributions} threshold={threshold} />
      <div className="fusion-detail-grid"><div className="contribution-waterfall"><h3>Log-odds contribution map</h3>{contributions.map(([label, value]) => <div className="contribution-row" key={label}><span>{label.replaceAll('_', ' ')}</span><div className="contribution-track"><i className="contribution-zero" /><b className={value >= 0 ? 'positive' : 'negative'} style={value >= 0 ? { left: '50%', width: `${Math.abs(value) / maxContribution * 48}%` } : { right: '50%', width: `${Math.abs(value) / maxContribution * 48}%` }} /></div><code className={value >= 0 ? 'positive-text' : 'negative-text'}>{value >= 0 ? '+' : ''}{value.toFixed(4)}</code></div>)}</div><div className="fusion-result"><span>Σ LOG ODDS</span><strong>{logOdds.toFixed(4)}</strong><i>σ</i><span>SIGMOID</span><strong>{logistic.toFixed(4)}</strong><div className={verification?.verified ? 'verified' : 'suppressed'}>{forcedAccept ? 'DEMO GATE ACCEPTED' : verification?.verified ? 'VERIFIED' : 'SUPPRESSED'}</div><small>{verification?.override_source ? `${verification.override_source} override activated the ≥90% floor` : forcedAccept ? `Raw fusion remains ${percent(fused)}; forced acceptance is shown separately` : 'No guarded sensor override was required'}</small></div></div>
      <div className="evidence-reasons">{verification?.evidence?.map((item, index) => <div key={item}><b>{String(index + 1).padStart(2, '0')}</b><span>{item}</span></div>)}</div>
    </section>

    <section className="analysis-stage intelligence-stage">
      <StageHeading number="04" eyebrow="Retrieved intelligence" title="What context shaped the decision?" />
      <div className="intelligence-layout">
        <div className="policy-visual"><h3>Policy relevance</h3>{audit.retrieval.evidence.map(item => <article key={`${item.document_id}-${item.chunk_position}`}><div className="policy-score"><svg viewBox="0 0 50 50" role="img" aria-label={`${percent(item.score)} policy relevance`}><circle cx="25" cy="25" r="19" pathLength="100" /><circle className="value" cx="25" cy="25" r="19" pathLength="100" strokeDasharray={`${clamp(item.score) * 100} 100`} /><text x="25" y="28">{Math.round(item.score * 100)}</text></svg></div><div><header><strong>{item.filename}</strong><span>chunk {item.chunk_position + 1}</span></header><p>{item.excerpt}</p></div></article>)}{!audit.retrieval.evidence.length && <p className="analysis-note">No policy chunks were retrieved.</p>}</div>
        <div className="memory-visual"><h3>Reviewed memory</h3>{reviews.map(review => <article key={review.incident_id}><div className="memory-match"><span style={{ width: percent(review.similarity) }} /></div><header><strong>{percent(review.similarity)} similar</strong><span>#{review.incident_id.slice(0, 8)}</span></header><p>{review.reviewed_severity.toUpperCase()} · {review.response_action}</p><small>{review.reason}</small></article>)}{!reviews.length && <div className="memory-empty"><strong>0</strong><span>similar reviewed incidents</span><small>This decision used policy and current evidence without a prior human correction.</small></div>}</div>
      </div>
      <MemoryInfluencePanel reviews={reviews} influence={memoryInfluence} currentSeverity={audit.decision.severity} currentAction={responseAction} />
    </section>

    <section className="analysis-stage agent-stage">
      <StageHeading number="05" eyebrow="Groq reasoning" title="Why was this action selected?" />
      <div className="decision-banner"><div><span>Severity</span><strong>{audit.decision.severity.toUpperCase()}</strong></div><p>“{audit.decision.alert_message}”</p><div><span>Action</span><strong>{responseAction.toUpperCase()}</strong></div></div>
      <div className="rationale-path">{audit.decision.rationale.map((item, index) => <div key={item}><b>{String(index + 1).padStart(2, '0')}</b><i /><p>{item}</p></div>)}</div>
      <div className="pipeline-map" aria-label="Evidence to action decision flow"><FlowNode label="Scan" value={`${percent(visual)} visual`} note={`${sensors.length} sensor inputs`} /><FlowArrow /><FlowNode label="Verify" value={percent(fused)} note={verification?.verified ? 'candidate accepted' : 'candidate suppressed'} /><FlowArrow /><FlowNode label="Retrieve" value={`${audit.retrieval.evidence.length} policy chunks`} note={`${reviews.length} memory matches`} /><FlowArrow /><FlowNode label="Reason" value={audit.decision.severity.toUpperCase()} note={audit.reasoning_model} /><FlowArrow /><FlowNode label="Act" value={responseAction.toUpperCase()} note={failures.length ? `${failures.length} failed` : `${successes.length} completed`} /></div>
    </section>

    <section className="analysis-stage delivery-stage">
      <StageHeading number="06" eyebrow="Action + memory" title="What happened after the decision?" />
      <div className="delivery-timeline">{audit.plan.actions.map((action, index) => { const delivery = deliveries.find(item => item.action_kind === action.kind && item.target === action.target); const status = delivery?.status ?? (action.kind === 'dashboard_alert' ? 'live event' : 'recorded'); return <article key={`${action.kind}-${action.target}`}><b>{index + 1}</b><i /><div><span>{action.kind.replaceAll('_', ' ')}</span><strong>{action.target}</strong><em className={status === 'failed' ? 'failed' : ''}>{status}</em></div></article> })}</div>
      <div className="analysis-actions"><button onClick={() => downloadIncidentReport(incident.incident_id)}>Download complete incident PDF ↓</button></div>
      <IncidentReview key={incident.incident_id} incidentId={incident.incident_id} initialSeverity={audit.decision.severity} initialAction={responseAction} />
    </section>
  </div>
}

function StageHeading({ number, eyebrow, title }: { number: string; eyebrow: string; title: string }) { return <div className="stage-heading"><div><span>{number}</span><p>{eyebrow}</p></div><h2>{title}</h2></div> }

type VerificationSnapshot = NonNullable<AgentAudit['retrieval']['verification_snapshot']>

export function AdaptiveThresholdVisualization({ verification, fused }: { verification?: VerificationSnapshot; fused: number }) {
  const base = verification?.base_decision_threshold ?? verification?.decision_threshold ?? .68
  const factory = verification?.default_decision_threshold ?? .68
  const final = verification?.decision_threshold ?? base
  const adjustment = verification?.threshold_adjustment ?? final - base
  const lower = verification?.threshold_minimum ?? .60
  const upper = verification?.threshold_maximum ?? .76
  const maximumAdjustment = verification?.threshold_maximum_adjustment ?? .08
  const stabilizer = verification?.threshold_stabilizer ?? 3
  const factors = verification?.threshold_factors ?? []
  const newlyAppliedFactors = factors.filter(factor => factor.applied_to_baseline !== false)
  const totalWeight = newlyAppliedFactors.reduce((sum, factor) => sum + factor.weight, 0)
  const signedWeight = newlyAppliedFactors.reduce((sum, factor) => sum + factor.signed_weight, 0)
  const changed = Math.abs(adjustment) >= .00005
  const direction = adjustment > 0 ? 'rose' : adjustment < 0 ? 'fell' : 'stayed'
  const headline = changed ? `Threshold ${direction} from ${percent(base)} to ${percent(final)}` : `Threshold stayed at ${percent(base)}`
  const baselineVerified = verification?.baseline_verified ?? Boolean(verification?.override_source || fused >= base)
  const adaptiveVerified = verification?.adaptive_verified ?? Boolean(verification?.override_source || fused >= final)
  const factorLabel = (effect: string) => ({
    raise_false_alarm: 'Prior false alarm · raise',
    raise_overestimated: 'Prior overestimate · raise',
    lower_underestimated: 'Prior underestimate · lower',
    conflicting_correction: 'Conflicting review · stabilize',
    unchanged: 'Confirmed decision · stabilize',
  }[effect] ?? effect.replaceAll('_', ' '))

  return <div className={`adaptive-threshold-visual ${changed ? direction : 'stable'}`} data-testid="adaptive-threshold-visual">
    <header>
      <div><span>Persistent adaptive decision boundary</span><h3>{headline}</h3><p>The learned result becomes this location's next baseline. Each review version is applied once; current sensor evidence is never counted twice.</p></div>
      <div className="threshold-delta"><small>Change</small><strong>{adjustment > 0 ? '+' : ''}{(adjustment * 100).toFixed(2)}<em> pp</em></strong></div>
    </header>
    <div className="threshold-rail-wrap">
      <div className="threshold-rail" aria-label={`Baseline ${percent(base)}, adaptive threshold ${percent(final)}, fused probability ${percent(fused)}`}>
        <div className="threshold-safe-window" style={{ left: percent(lower), width: percent(upper - lower) }} />
        <ThresholdMarker className="minimum" label="Hard floor" value={lower} />
        {Math.abs(factory - base) >= .00005 && <ThresholdMarker className="factory" label="Original 68%" value={factory} />}
        <ThresholdMarker className="baseline" label="Learned baseline" value={base} />
        {changed && <ThresholdMarker className="adaptive" label="Adaptive" value={final} />}
        <ThresholdMarker className="maximum" label="Hard ceiling" value={upper} />
        <ThresholdMarker className="fused" label="Fused evidence" value={fused} />
      </div>
      <div className="threshold-scale"><span>0%</span><span>Safe adjustment window {percent(lower)}–{percent(upper)}</span><span>100%</span></div>
    </div>
    <div className="threshold-math-grid">
      <div className="threshold-equation">
        <span>BOUND</span><strong>{percent(maximumAdjustment)}</strong><b>×</b><span>SIGNED WEIGHT</span><strong>{signedWeight.toFixed(3)}</strong><b>÷</b><span>STABILIZER + WEIGHT</span><strong>{stabilizer.toFixed(1)} + {totalWeight.toFixed(3)}</strong><b>=</b><span>ADJUSTMENT</span><strong className={adjustment > 0 ? 'raise' : adjustment < 0 ? 'lower' : ''}>{adjustment > 0 ? '+' : ''}{(adjustment * 100).toFixed(2)} pp</strong>
      </div>
      <div className="threshold-outcome-comparison">
        <OutcomeCard label="Baseline outcome" threshold={base} verified={baselineVerified} />
        <i>→</i>
        <OutcomeCard label="Adaptive outcome" threshold={final} verified={adaptiveVerified} />
        {verification?.forced_accept && <div className="threshold-demo-gate"><span>Demo gate</span><strong>ACCEPTED</strong><small>Shown separately from the statistical result</small></div>}
      </div>
    </div>
    <div className="threshold-factor-deck">
      <header><div><strong>Reviewed-memory pressure</strong><small>Similarity × time decay × correction direction</small></div><span>{factors.length} comparable review{factors.length === 1 ? '' : 's'}</span></header>
      {factors.length ? <div className="threshold-factor-list">{factors.map((factor, index) => <article key={`${factor.incident_id}-${index}`} className={factor.direction > 0 ? 'raise' : factor.direction < 0 ? 'lower' : 'stable'}>
        <div className="factor-direction"><b>{factor.direction > 0 ? '↑' : factor.direction < 0 ? '↓' : '•'}</b><span>{factorLabel(factor.effect)}</span></div>
        <div className="factor-source"><strong>#{factor.incident_id.slice(0, 8)}</strong><small>{factor.reviewed_severity.toUpperCase()} · {factor.response_action} · {factor.age_days.toFixed(1)} days old</small></div>
        <div className="factor-math"><span>{percent(factor.similarity)}</span><b>×</b><span>{percent(factor.recency)}</span><b>=</b><strong>{factor.weight.toFixed(3)}</strong></div>
        <div className="factor-pressure"><span>{factor.already_learned ? 'already in baseline' : 'new signed pressure'}</span><strong>{factor.already_learned ? 'REUSED' : `${factor.signed_weight > 0 ? '+' : ''}${factor.signed_weight.toFixed(3)}`}</strong></div>
        <p>{factor.reason || 'No reviewer note recorded.'}</p>
      </article>)}</div> : <div className="threshold-factor-empty"><strong>Baseline protected</strong><span>No comparable human-reviewed incident exerted directional pressure, so the threshold did not move.</span></div>}
    </div>
  </div>
}

function ThresholdMarker({ className, label, value }: { className: string; label: string; value: number }) {
  return <div className={`threshold-marker ${className}`} style={{ left: percent(value) }}><span>{label}</span><b>{percent(value)}</b><i /></div>
}

function OutcomeCard({ label, threshold, verified }: { label: string; threshold: number; verified: boolean }) {
  return <div className={`threshold-outcome ${verified ? 'accepted' : 'suppressed'}`}><span>{label}</span><strong>{verified ? 'ACCEPTED' : 'SUPPRESSED'}</strong><small>boundary {percent(threshold)}</small></div>
}

function RiskDial({ label, value, caption, emphasized = false }: { label: string; value: number; caption: string; emphasized?: boolean }) { const normalized = clamp(value); return <div className={`risk-dial ${emphasized ? 'emphasized' : ''}`}><svg viewBox="0 0 132 132" role="img" aria-label={`${label}: ${percent(normalized)}`}><circle className="dial-track" cx="66" cy="66" r="52" pathLength="100" /><circle className="dial-value" cx="66" cy="66" r="52" pathLength="100" strokeDasharray={`${normalized * 100} 100`} /><text className="dial-number" x="66" y="70">{Math.round(normalized * 100)}</text><text className="dial-unit" x="66" y="86">PERCENT</text></svg><div><strong>{label}</strong><small>{caption}</small></div></div> }

function QualityBar({ label, value }: { label: string; value: number }) { return <label><span>{label}</span><i><b style={{ width: percent(value) }} /></i><em>{percent(value)}</em></label> }

type SensorTimeline = NonNullable<NonNullable<AgentAudit['retrieval']['scan_snapshot']>['sensor_timeline']>

export function SensorTimelineVisualization({ timeline, candidateTimestamp, scenario }: { timeline: SensorTimeline; candidateTimestamp: number | null; scenario: string }) {
  if (!timeline.length) return <div className="sensor-timeline-empty">This older audit does not contain per-frame sensor readings.</div>
  const sensorTypes = [...new Set(timeline.flatMap(sample => sample.readings.map(reading => reading.sensor_type)))]
  const probabilitySeries = sensorTypes.map(sensorType => ({
    label: sensorType,
    values: timeline.map(sample => ({ timestamp: sample.timestamp_ms, value: sample.readings.find(reading => reading.sensor_type === sensorType)?.probability ?? 0 })),
  }))
  const reliabilitySeries = sensorTypes.map(sensorType => ({
    label: sensorType,
    values: timeline.map(sample => { const reading = sample.readings.find(item => item.sensor_type === sensorType); return { timestamp: sample.timestamp_ms, value: reading ? effectiveReliability(reading.reliability, reading.age_ms) : 0 } }),
  }))
  return <div className="sensor-timeline-visual" data-testid="sensor-timeline-visual">
    <header><div><span>Generated temporal evidence</span><h3>Every processed frame has a synchronized sensor reading</h3></div><div><strong>{timeline.length}</strong><small>frames · {scenario.replaceAll('_', ' ') || 'synthetic scenario'}</small></div></header>
    <div className="sensor-chart-grid">
      <SensorLineChart title="Signal probability" series={probabilitySeries} timeline={timeline} candidateTimestamp={candidateTimestamp} threshold={.7} />
      <SensorLineChart title="Effective reliability" series={reliabilitySeries} timeline={timeline} candidateTimestamp={candidateTimestamp} threshold={.5} />
    </div>
    <div className="sensor-frame-matrix" style={{ '--sensor-frame-count': timeline.length } as CSSProperties} aria-label="Per-frame sensor probability heatmap">
      <div className="matrix-time-axis"><span>FRAME</span>{timeline.map(sample => <b key={sample.frame_index}>{sample.frame_index + 1}</b>)}</div>
      {sensorTypes.map(sensorType => <div className="matrix-row" key={sensorType}><span>{sensorType}</span>{timeline.map(sample => { const reading = sample.readings.find(item => item.sensor_type === sensorType); const value = reading?.probability ?? 0; return <i key={sample.frame_index} style={{ '--sensor-level': value } as CSSProperties} title={`Frame ${sample.frame_index + 1} · ${(sample.timestamp_ms / 1000).toFixed(2)}s · ${sensorType} ${percent(value)} · reliability ${percent(reading?.reliability ?? 0)}`}><b>{Math.round(value * 100)}</b></i> })}</div>)}
    </div>
    <footer><span><i className="smoke" /> Smoke</span><span><i className="audio" /> Audio</span><span><i className="candidate" /> Selected incident frame</span><small>Hover a frame cell for its exact generated values.</small></footer>
  </div>
}

function SensorLineChart({ title, series, timeline, candidateTimestamp, threshold }: { title: string; series: { label: string; values: { timestamp: number; value: number }[] }[]; timeline: SensorTimeline; candidateTimestamp: number | null; threshold: number }) {
  const left = 54; const right = 846; const top = 22; const bottom = 178
  const firstTime = timeline[0].timestamp_ms
  const lastTime = timeline.at(-1)?.timestamp_ms ?? firstTime
  const x = (timestamp: number) => lastTime === firstTime ? (left + right) / 2 : left + (timestamp - firstTime) / (lastTime - firstTime) * (right - left)
  const y = (value: number) => bottom - clamp(value) * (bottom - top)
  return <div className="sensor-line-chart"><h4>{title}</h4><svg viewBox="0 0 900 220" role="img" aria-label={`${title} for smoke and audio across ${timeline.length} frames`}>
    {[0, .25, .5, .75, 1].map(value => <g key={value}><line className="sensor-gridline" x1={left} x2={right} y1={y(value)} y2={y(value)} /><text className="sensor-axis-label" x={left - 10} y={y(value) + 3}>{Math.round(value * 100)}</text></g>)}
    <line className="sensor-chart-threshold" x1={left} x2={right} y1={y(threshold)} y2={y(threshold)} /><text className="sensor-threshold-label" x={right} y={y(threshold) - 5}>{percent(threshold)} gate</text>
    {candidateTimestamp != null && <><line className="sensor-candidate-line" x1={x(candidateTimestamp)} x2={x(candidateTimestamp)} y1={top} y2={bottom} /><text className="sensor-candidate-label" x={x(candidateTimestamp)} y={top - 7}>INCIDENT</text></>}
    {series.map(item => <g className={`sensor-series ${item.label}`} key={item.label}><polyline points={item.values.map(point => `${x(point.timestamp)},${y(point.value)}`).join(' ')} />{item.values.map((point, index) => <circle key={index} cx={x(point.timestamp)} cy={y(point.value)} r="2.7"><title>{`${item.label} · frame ${timeline[index].frame_index + 1} · ${percent(point.value)}`}</title></circle>)}</g>)}
    <line className="sensor-axis" x1={left} x2={right} y1={bottom} y2={bottom} /><text className="sensor-time-start" x={left} y={bottom + 23}>{(firstTime / 1000).toFixed(1)}s</text><text className="sensor-time-end" x={right} y={bottom + 23}>{(lastTime / 1000).toFixed(1)}s</text>
  </svg></div>
}

function ProbabilityJourney({ contributions, threshold }: { contributions: [string, number][]; threshold: number }) {
  const steps = contributions.map(([label, value], index) => { const cumulative = contributions.slice(0, index + 1).reduce((sum, [, item]) => sum + item, 0); return { label, value, probability: 1 / (1 + Math.exp(-cumulative)) } })
  if (!steps.length) return <div className="analysis-note">No stored fusion contributions are available.</div>
  const left = 64; const right = 846; const top = 24; const bottom = 184
  const x = (index: number) => steps.length === 1 ? (left + right) / 2 : left + index * (right - left) / (steps.length - 1)
  const y = (probability: number) => bottom - clamp(probability) * (bottom - top)
  const points = steps.map((step, index) => `${x(index)},${y(step.probability)}`).join(' ')
  return <div className="probability-journey"><svg viewBox="0 0 910 235" role="img" aria-label="Cumulative fused probability after each evidence contribution"><line className="journey-threshold" x1={left} x2={right} y1={y(threshold)} y2={y(threshold)} /><text className="journey-threshold-label" x={right} y={y(threshold) - 7}>verification threshold {percent(threshold)}</text><line className="journey-axis" x1={left} x2={right} y1={bottom} y2={bottom} /><polyline className="journey-line" points={points} />{steps.map((step, index) => <g key={`${step.label}-${index}`}><line className="journey-guide" x1={x(index)} x2={x(index)} y1={y(step.probability)} y2={bottom} /><circle cx={x(index)} cy={y(step.probability)} r="7" /><text className="journey-value" x={x(index)} y={y(step.probability) - 13}>{percent(step.probability)}</text><text className="journey-label" x={x(index)} y={bottom + 22}>{step.label.replaceAll('_', ' ')}</text><text className={step.value >= 0 ? 'journey-delta positive-text' : 'journey-delta negative-text'} x={x(index)} y={bottom + 38}>{step.value >= 0 ? '+' : ''}{step.value.toFixed(2)}</text></g>)}</svg></div>
}

function FlowNode({ label, value, note }: { label: string; value: string; note: string }) { return <div className="flow-node"><span>{label}</span><strong>{value}</strong><small>{note}</small></div> }
function FlowArrow() { return <div className="flow-arrow"><i />→</div> }

type ReviewedIncident = NonNullable<AgentAudit['retrieval']['reviewed_incidents']>[number]
type MemoryInfluence = NonNullable<AgentAudit['decision']['memory_influence']>

function MemoryInfluencePanel({ reviews, influence, currentSeverity, currentAction }: { reviews: ReviewedIncident[]; influence?: MemoryInfluence; currentSeverity: Severity; currentAction: string }) {
  const cited = influence ? reviews.filter(review => influence.incident_ids.includes(review.incident_id)) : []
  const strongest = cited[0] ?? reviews[0]
  const state = influence?.applied ? 'applied' : influence ? 'considered' : reviews.length ? 'unrecorded' : 'none'
  const status = state === 'applied' ? 'Previous incident influenced this decision' : state === 'considered' ? 'Previous incidents did not change this decision' : state === 'unrecorded' ? 'Influence was not recorded for this older audit' : 'No previous incident was available to influence this decision'
  return <div className={`memory-influence-panel ${state}`} data-testid="memory-influence-panel">
    <header><div><span className="memory-influence-kicker">Memory influence audit</span><h3>{status}</h3></div><b>{state === 'applied' ? `${percent(influence?.weight ?? strongest?.influence_weight ?? 0)} · ${influence?.effect.toUpperCase()}` : state.toUpperCase()}</b></header>
    {strongest ? <div className="memory-influence-flow">
      <div className="memory-history-node"><span>Previous AI decision</span><strong>{strongest.original_decision?.severity?.toUpperCase() ?? 'NOT RECORDED'}</strong><small>{strongest.original_decision?.response_action ?? 'unknown action'} · #{strongest.incident_id.slice(0, 8)}</small></div>
      <div className="memory-flow-link"><i style={{ '--memory-match': percent(strongest.similarity) } as CSSProperties} /><strong>{percent(strongest.similarity)}</strong><span>evidence match</span></div>
      <div className="memory-review-node"><span>Human correction</span><strong>{strongest.reviewed_severity.toUpperCase()}</strong><small>{strongest.response_action} · {strongest.false_alarm ? 'false alarm' : 'valid incident'}</small></div>
      <div className={`memory-effect-node ${influence?.effect ?? 'none'}`}><span>Effect on Groq</span><strong>{influence?.applied ? influence.effect.toUpperCase() : 'NO CHANGE'}</strong><small>{influence?.applied ? `${percent(influence.weight ?? strongest.influence_weight ?? strongest.similarity)} influence weight` : 'current evidence prevailed'}</small></div>
      <div className="memory-current-node"><span>Current decision</span><strong>{currentSeverity.toUpperCase()}</strong><small>{currentAction}</small></div>
    </div> : <div className="memory-influence-empty"><span>Current evidence</span><i>→</i><strong>{currentSeverity.toUpperCase()} · {currentAction.toUpperCase()}</strong></div>}
    {influence?.method === 'similarity_weighted_human_review_v1' && <div className="memory-reconciliation-equation">
      <div><span>Current AI draft</span><strong>{influence.base_severity?.toUpperCase()} · {influence.base_action?.toUpperCase()}</strong><small>{percent(influence.current_weight ?? 0)} weight</small></div>
      <b>+</b>
      <div><span>Human-reviewed outcome</span><strong>{influence.reviewed_severity?.toUpperCase()} · {influence.reviewed_action?.toUpperCase()}</strong><small>{percent(influence.weight ?? 0)} similarity weight · severity floor {influence.reviewed_severity_floor?.toUpperCase() ?? 'LOW'}</small></div>
      <b>=</b>
      <div className="memory-reconciliation-result"><span>Reconciled decision</span><strong>{currentSeverity.toUpperCase()} · {currentAction.toUpperCase()}</strong><small>ordinal scores {influence.severity_score?.toFixed(2)} / {influence.action_score?.toFixed(2)}</small></div>
    </div>}
    {strongest?.feature_matches?.length ? <FeatureMatchBreakdown review={strongest} applied={Boolean(influence?.applied && influence.incident_ids.includes(strongest.incident_id))} /> : null}
    <p>{influence?.explanation ?? (reviews.length ? 'This audit predates structured memory-influence tracking, so Sentrix will not infer whether the retrieved review changed Groq’s decision.' : 'No sufficiently similar, human-reviewed incident was retrieved for this event.')}</p>
    {influence?.applied && cited.length > 1 && <div className="memory-citations">Cited incidents: {cited.map(review => `#${review.incident_id.slice(0, 8)}`).join(' · ')}</div>}
  </div>
}

function FeatureMatchBreakdown({ review, applied }: { review: ReviewedIncident; applied: boolean }) {
  const features = review.feature_matches ?? []
  const formatValue = (feature: NonNullable<ReviewedIncident['feature_matches']>[number], value: number) => feature.key.endsWith('freshness') ? `${Math.round(value)}ms` : percent(value)
  return <div className="memory-match-breakdown">
    <div className="match-score-orbit"><svg viewBox="0 0 120 120" role="img" aria-label={`${percent(review.influence_weight ?? review.similarity)} previous incident influence weight`}><circle cx="60" cy="60" r="47" pathLength="100" /><circle className="value" cx="60" cy="60" r="47" pathLength="100" strokeDasharray={`${(review.influence_weight ?? review.similarity) * 100} 100`} /><text x="60" y="58">{Math.round((review.influence_weight ?? review.similarity) * 100)}%</text><text className="caption" x="60" y="73">MATCH WEIGHT</text></svg><small>{applied ? 'Applied to Groq decision' : 'Retrieved for comparison'}</small></div>
    <div className="feature-match-chart"><header><div><strong>Full evidence fingerprint</strong><small>Previous clip versus current clip</small></div><span>Match × weight = influence</span></header>{features.map(feature => <div className="feature-match-row" key={feature.key}><div><strong>{feature.label}</strong><small>{formatValue(feature, feature.previous)} previous · {formatValue(feature, feature.current)} current</small></div><div className="feature-match-track"><i style={{ width: percent(feature.match) }} /><b style={{ left: percent(feature.match) }} /></div><code>{percent(feature.match)}</code><em>× {percent(feature.weight)}</em><strong>{percent(feature.weighted_match)}</strong></div>)}</div>
    <div className="sensor-match-summary"><span>Sensor-profile agreement</span>{review.sensor_matches?.map(sensor => <div key={sensor.sensor_type}><header><strong>{sensor.sensor_type}</strong><b>{percent(sensor.match)}</b></header><i><b style={{ width: percent(sensor.match) }} /></i><small>{percent(sensor.weight)} of total memory weight</small></div>)}</div>
  </div>
}
