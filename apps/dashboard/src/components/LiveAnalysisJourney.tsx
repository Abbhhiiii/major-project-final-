import { useEffect, useMemo, useRef, type CSSProperties, type ReactNode, type RefObject } from 'react'

import { Icon } from './Icon'
import type { ProcessingJob, SensorFrameSample, StageEvent } from '../types'

type Payload = Record<string, unknown>

const pct = (value: unknown) => `${Math.round(Number(value ?? 0) * 100)}%`
const list = <T,>(value: unknown) => (Array.isArray(value) ? value as T[] : [])
const routeStages = ['Frames', 'Verify', 'Retrieve', 'Reason', 'Plan', 'Act']

export function LiveAnalysisJourney({ frames, processingJob, events, isProcessing }: { frames: SensorFrameSample[]; processingJob: ProcessingJob | null; events: StageEvent[]; isProcessing: boolean }) {
  const byStage = useMemo(() => new Map(events.map(event => [event.stage, event.payload])), [events])
  const scanRef = useRef<HTMLElement>(null)
  const verificationRef = useRef<HTMLElement>(null)
  const retrievalRef = useRef<HTMLElement>(null)
  const reasoningRef = useRef<HTMLElement>(null)
  const planningRef = useRef<HTMLElement>(null)
  const actionRef = useRef<HTMLElement>(null)
  const lastMilestone = useRef('')
  const hasRun = Boolean(processingJob || frames.length || events.length)

  const milestone = byStage.has('execution') || byStage.has('memory') ? 'action'
    : byStage.has('planning') ? 'planning'
      : byStage.has('reasoning') ? 'reasoning'
        : byStage.has('context_retrieval') ? 'retrieval'
          : byStage.has('verification') ? 'verification'
            : hasRun ? 'scan' : ''
  const routeIndex = milestone ? ({ scan: 0, verification: 1, retrieval: 2, reasoning: 3, planning: 4, action: 5 } as Record<string, number>)[milestone] ?? 0 : 0

  useEffect(() => {
    if (!milestone) { lastMilestone.current = ''; return }
    if (milestone === lastMilestone.current) return
    lastMilestone.current = milestone
    const targets: Record<string, RefObject<HTMLElement | null>> = { scan: scanRef, verification: verificationRef, retrieval: retrievalRef, reasoning: reasoningRef, planning: planningRef, action: actionRef }
    const timer = window.setTimeout(() => {
      const target = targets[milestone]?.current
      if (!target) return
      const top = target.getBoundingClientRect().top + window.scrollY - 24
      window.scrollTo({ top, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    }, 320)
    return () => window.clearTimeout(timer)
  }, [milestone])

  if (!hasRun) return <section className="panel live-journey-empty"><span><Icon name="activity" /></span><div><strong>Guided analysis is ready</strong><p>Run the uploaded footage to watch every frame, verification calculation, retrieval, agent decision, and action appear in sequence.</p></div></section>

  const detection = byStage.get('detection')
  const verification = byStage.get('verification')
  const retrieval = byStage.get('context_retrieval')
  const reasoning = byStage.get('reasoning')
  const planning = byStage.get('planning')
  const execution = byStage.get('execution')
  const memory = byStage.get('memory')

  return <div className="live-analysis-journey" aria-label="Live guided pipeline analysis">
    <div className="live-journey-route" aria-label="Guided analysis progress">{routeStages.map((label, index) => <div key={label} className={index < routeIndex ? 'done' : index === routeIndex ? 'active' : ''}><span>{index < routeIndex ? '✓' : String(index + 1).padStart(2, '0')}</span><strong>{label}</strong>{index < routeStages.length - 1 && <i />}</div>)}</div>
    <FrameStage sectionRef={scanRef} frames={frames} job={processingJob} detection={detection} active={!verification && isProcessing} />
    {verification && <VerificationStage sectionRef={verificationRef} payload={verification} active={!retrieval && isProcessing} />}
    {retrieval && <RetrievalStage sectionRef={retrievalRef} payload={retrieval} active={!reasoning && isProcessing} />}
    {reasoning && <ReasoningStage sectionRef={reasoningRef} payload={reasoning} active={!planning && isProcessing} />}
    {planning && <PlanningStage sectionRef={planningRef} payload={planning} active={!execution && isProcessing} />}
    {(execution || memory) && <ActionStage sectionRef={actionRef} execution={execution} memory={memory} active={!memory && isProcessing} />}
  </div>
}

function StageShell({ sectionRef, number, eyebrow, title, state, children }: { sectionRef: RefObject<HTMLElement | null>; number: string; eyebrow: string; title: string; state: 'live' | 'complete'; children: ReactNode }) {
  return <section ref={sectionRef} className={`panel live-demo-stage ${state === 'live' ? 'is-live' : 'is-complete'}`}>
    <header><div className="live-stage-number">{number}</div><div><p>{eyebrow}</p><h2>{title}</h2></div><span className="live-stage-state"><i />{state}</span></header>
    <div className="live-stage-body">{children}</div>
  </section>
}

function FrameStage({ sectionRef, frames, job, detection, active }: { sectionRef: RefObject<HTMLElement | null>; frames: SensorFrameSample[]; job: ProcessingJob | null; detection?: Payload; active: boolean }) {
  const visibleFrames = frames
  return <StageShell sectionRef={sectionRef} number="01" eyebrow="Multimodal scan" title="Frame-by-frame visual and sensor evidence" state={active ? 'live' : 'complete'}>
    <div className="live-scan-summary"><div><span>Frames processed</span><strong>{job?.frames_processed ?? frames.length}</strong></div><div><span>Scan progress</span><strong>{Math.round(job?.progress_percent ?? (detection ? 100 : 0))}%</strong></div><div><span>CV candidates</span><strong>{job?.detections_found ?? (detection ? 1 : 0)}</strong></div><div><span>Sensor mode</span><strong>{(job?.sensor_scenario || String(detection?.sensor_scenario ?? 'waiting')).replaceAll('_', ' ')}</strong></div></div>
    <SensorSignalPlot frames={visibleFrames} />
    <div className="live-frame-rail" style={{ '--frame-progress': `${job?.progress_percent ?? 0}%` } as CSSProperties}>
      <div className="live-frame-progress"><i /></div>
      {visibleFrames.length ? visibleFrames.map(frame => <article key={frame.frame_index} className="live-frame-card"><header><b>F{String(frame.frame_index + 1).padStart(2, '0')}</b><time>{(frame.timestamp_ms / 1000).toFixed(2)}s</time></header>{frame.readings.map(reading => <div key={reading.sensor_type}><span>{reading.sensor_type}</span><strong>{pct(reading.probability)}</strong><i><b style={{ width: pct(reading.probability) }} /></i><small>{pct(reading.reliability)} reliable</small></div>)}</article>) : <div className="live-stage-waiting">Waiting for the first decoded frame and synchronized sensor sample…</div>}
    </div>
    <p className="live-stage-note">Every tile is emitted by the backend for one decoded frame. The visual detector and synchronized smoke/audio twin run before a candidate enters verification.</p>
  </StageShell>
}

function VerificationStage({ sectionRef, payload, active }: { sectionRef: RefObject<HTMLElement | null>; payload: Payload; active: boolean }) {
  const contributions = Object.entries((payload.contributions as Record<string, number> | undefined) ?? {})
  const z = contributions.reduce((sum, [, value]) => sum + Number(value), 0)
  const calculated = 1 / (1 + Math.exp(-z))
  return <StageShell sectionRef={sectionRef} number="02" eyebrow="Statistical verification" title="How the fused probability was calculated" state={active ? 'live' : 'complete'}>
    <div className="verification-equation-live"><div><span>Σ weighted log-odds</span><strong>{z.toFixed(4)}</strong></div><b>→</b><div><span>σ(z) fused probability</span><strong>{pct(payload.fused_probability ?? calculated)}</strong></div><b>vs</b><div><span>Adaptive threshold</span><strong>{pct(payload.decision_threshold ?? .68)}</strong></div><b>→</b><div className={payload.verified ? 'accepted' : 'suppressed'}><span>Verification result</span><strong>{payload.verified ? 'ACCEPTED' : 'SUPPRESSED'}</strong></div></div>
    <div className="contribution-live-grid">{contributions.map(([name, value]) => <article key={name}><header><span>{name.replaceAll('_', ' ')}</span><strong>{Number(value) >= 0 ? '+' : ''}{Number(value).toFixed(3)}</strong></header><i><b className={Number(value) < 0 ? 'negative' : ''} style={{ width: `${Math.min(100, Math.abs(Number(value)) / 2 * 100)}%` }} /></i></article>)}</div>
    <div className="live-threshold-rail"><i style={{ left: pct(payload.decision_threshold ?? .68) }}><span>threshold {pct(payload.decision_threshold ?? .68)}</span></i><b style={{ width: pct(payload.fused_probability ?? calculated) }} /><strong style={{ left: pct(payload.fused_probability ?? calculated) }}>{pct(payload.fused_probability ?? calculated)}</strong></div>
    {Boolean(payload.override_source) && <p className="live-override-banner">Guarded override applied: <strong>{String(payload.override_source).replaceAll('_', ' ')}</strong></p>}
    <div className="live-evidence-list">{list<string>(payload.evidence).map((item, index) => <p key={item}><b>{String(index + 1).padStart(2, '0')}</b>{item}</p>)}</div>
  </StageShell>
}

function RetrievalStage({ sectionRef, payload, active }: { sectionRef: RefObject<HTMLElement | null>; payload: Payload; active: boolean }) {
  const evidence = list<{ filename: string; score: number; excerpt: string; chunk_position: number }>(payload.evidence)
  const reviews = list<{ incident_id: string; similarity: number; reviewed_severity: string; response_action: string; reason: string }>(payload.reviewed_incidents)
  const policyStrength = Math.max(0, ...evidence.map(item => Number(item.score)))
  const memoryStrength = Math.max(0, ...reviews.map(item => Number(item.similarity)))
  return <StageShell sectionRef={sectionRef} number="03" eyebrow="Context retrieval" title="Policy and previous intelligence retrieved" state={active ? 'live' : 'complete'}>
    <div className="live-context-influence" aria-label="Retrieved context influence"><div><header><span>Policy relevance</span><strong>{pct(policyStrength)}</strong></header><i><b style={{ width: pct(policyStrength) }} /></i></div><em>decision context</em><div><header><span>Memory similarity</span><strong>{pct(memoryStrength)}</strong></header><i><b className="memory" style={{ width: pct(memoryStrength) }} /></i></div></div>
    <div className="live-retrieval-grid"><div><h3>RAG policy evidence <span>{evidence.length}</span></h3>{evidence.length ? evidence.map(item => <article key={`${item.filename}-${item.chunk_position}`}><div className="retrieval-score" style={{ '--score': pct(item.score) } as CSSProperties}>{pct(item.score)}</div><div><strong>{item.filename}</strong><small>Policy chunk {item.chunk_position + 1}</small><p>{item.excerpt}</p></div></article>) : <div className="live-stage-waiting">No matching policy chunk was returned.</div>}</div><div><h3>Reviewed incident memory <span>{reviews.length}</span></h3>{reviews.length ? reviews.map(review => <article key={review.incident_id}><div className="retrieval-score memory">{pct(review.similarity)}</div><div><strong>#{review.incident_id.slice(0, 8)} · {review.reviewed_severity}</strong><small>Human correction: {review.response_action}</small><p>{review.reason}</p></div></article>) : <div className="live-stage-waiting">No comparable human-reviewed incident influenced this decision.</div>}</div></div>
  </StageShell>
}

function ReasoningStage({ sectionRef, payload, active }: { sectionRef: RefObject<HTMLElement | null>; payload: Payload; active: boolean }) {
  return <StageShell sectionRef={sectionRef} number="04" eyebrow="Groq agent reasoning" title="Why the agent selected this response" state={active ? 'live' : 'complete'}>
    <div className="live-agent-decision"><div><span>Severity</span><strong>{String(payload.severity ?? 'assessing').toUpperCase()}</strong></div><blockquote>{String(payload.alert_message ?? 'The agent is constructing a policy-grounded response…')}</blockquote><div><span>Chosen action</span><strong>{String(payload.response_action ?? 'pending').toUpperCase()}</strong></div></div>
    <div className="live-rationale-path">{list<string>(payload.rationale).map((item, index) => <article key={`${index}-${item}`}><b>{String(index + 1).padStart(2, '0')}</b><i /><p>{item}</p></article>)}</div>
    <footer className="live-model-line"><Icon name="spark" /><span>Reasoned by {String(payload.provider ?? 'Groq')} · {String(payload.model ?? 'configured model')}</span></footer>
  </StageShell>
}

function PlanningStage({ sectionRef, payload, active }: { sectionRef: RefObject<HTMLElement | null>; payload: Payload; active: boolean }) {
  const actions = list<{ kind: string; target: string; message: string }>(payload.actions)
  return <StageShell sectionRef={sectionRef} number="05" eyebrow="Action planning" title="The decision becomes an executable plan" state={active ? 'live' : 'complete'}>
    <div className="live-plan-map"><span>AGENT DECISION</span><i /><strong>{actions.length} ACTION{actions.length === 1 ? '' : 'S'}</strong><i /><span>EXECUTION QUEUE</span></div>
    <div className="live-action-plan">{actions.map((action, index) => <article key={`${action.kind}-${index}`} data-kind={action.kind}><b>{index + 1}</b><i /><div><span>{action.kind.replaceAll('_', ' ')}</span><strong>{action.target}</strong><p>{action.message}</p></div></article>)}</div>
  </StageShell>
}

function SensorSignalPlot({ frames }: { frames: SensorFrameSample[] }) {
  const windowed = frames.slice(-30)
  const sensorNames = Array.from(new Set(windowed.flatMap(frame => frame.readings.map(reading => reading.sensor_type)))).slice(0, 4)
  const colors = ['#175996', '#d66b67', '#4b9f87', '#8b70b7']
  const width = 900
  const height = 150
  const x = (index: number) => windowed.length < 2 ? width / 2 : (index / (windowed.length - 1)) * width
  const y = (value: number) => height - Math.max(0, Math.min(1, value)) * height
  return <div className="live-signal-visual"><header><div><span>Live signal field</span><strong>Last {windowed.length || 0} synchronized frames</strong></div><div className="live-signal-legend">{sensorNames.map((name, index) => <span key={name}><i style={{ background: colors[index] }} />{name}</span>)}</div></header>
    {windowed.length ? <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Sensor probability by frame">
      {[.25, .5, .75].map(level => <line key={level} x1="0" x2={width} y1={y(level)} y2={y(level)} className="signal-grid-line" />)}
      {sensorNames.map((name, sensorIndex) => <polyline key={name} points={windowed.map((frame, index) => `${x(index)},${y(frame.readings.find(reading => reading.sensor_type === name)?.probability ?? 0)}`).join(' ')} fill="none" stroke={colors[sensorIndex]} strokeWidth="4" vectorEffect="non-scaling-stroke" />)}
    </svg> : <div className="live-signal-empty">Signal graph will draw as frames arrive</div>}
    <footer><span>0%</span><i /><span>100%</span></footer>
  </div>
}

function ActionStage({ sectionRef, execution, memory, active }: { sectionRef: RefObject<HTMLElement | null>; execution?: Payload; memory?: Payload; active: boolean }) {
  const successful = list<string>(execution?.successful_actions)
  const failed = list<string>(execution?.failed_actions)
  return <StageShell sectionRef={sectionRef} number="06" eyebrow="Execution and memory" title="Action outcome and durable incident record" state={active ? 'live' : 'complete'}>
    <div className="live-execution-grid"><div className="successful"><span>Completed actions</span><strong>{successful.length}</strong>{successful.map(item => <p key={item}>✓ {item}</p>)}</div><div className={failed.length ? 'failed' : 'successful'}><span>Failed actions</span><strong>{failed.length}</strong>{failed.length ? failed.map(item => <p key={item}>× {item}</p>) : <p>No delivery failures</p>}</div><div className="memory"><span>Incident memory</span><strong>{memory ? 'STORED' : 'WRITING'}</strong><p>{memory ? `#${String(memory.incident_id ?? '').slice(0, 8)} · ${String(memory.severity ?? '').toUpperCase()}` : 'Saving evidence, decision, and outcome…'}</p></div></div>
  </StageShell>
}
