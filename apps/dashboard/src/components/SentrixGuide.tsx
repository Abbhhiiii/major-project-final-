import { useEffect, useMemo, useState } from 'react'

import type { ProcessingJob, SensorFrameSample, StageEvent } from '../types'

type GuideProps = {
  frames: SensorFrameSample[]
  processingJob: ProcessingJob | null
  events: StageEvent[]
  isProcessing: boolean
}

const tourSteps = [
  { target: '.workspace-nav', eyebrow: 'Workspace navigation', title: 'Everything has its own room', copy: 'Operations runs the live workflow. History & Analytics reconstructs every decision. Policies stores the rules and contacts that ground the agent.' },
  { target: '.operations-scan', eyebrow: '01 · Evidence', title: 'This is the camera workspace', copy: 'Upload footage, choose a synthetic sensor scenario, confirm the map location, then run the analysis. The model and sensor twin process the same timeline.' },
  { target: '.operations-track', eyebrow: '02 · Pipeline', title: 'This tracker confirms every hand-off', copy: 'Detection, verification, retrieval, reasoning, planning, execution, and memory are separate stages. A check appears only after a real stage event arrives.' },
  { target: '.operations-response', eyebrow: '03 · Guided explanation', title: 'The evidence story appears here', copy: 'During a run, Sentrix automatically moves through large visual cards showing frame signals, fusion mathematics, retrieved intelligence, reasoning, and actions.' },
]

const percent = (value: unknown) => `${Math.round(Number(value ?? 0) * 100)}%`

function latestByStage(events: StageEvent[]) {
  return new Map(events.map(event => [event.stage, event.payload]))
}

function liveNarration(frames: SensorFrameSample[], job: ProcessingJob | null, events: StageEvent[], isProcessing: boolean) {
  const stages = latestByStage(events)
  const memory = stages.get('memory')
  const execution = stages.get('execution')
  const planning = stages.get('planning')
  const reasoning = stages.get('reasoning')
  const retrieval = stages.get('context_retrieval')
  const verification = stages.get('verification')
  const detection = stages.get('detection')
  const latestFrame = frames.at(-1)

  if (memory) return { mood: 'success', stage: 'Memory stored', headline: 'The incident is now reusable intelligence.', copy: `Record #${String(memory.incident_id ?? '').slice(0, 8)} was saved with a ${String(memory.severity ?? 'reviewable')} outcome. A human review can influence similar cases later.`, metrics: [['Status', 'Stored'], ['Severity', String(memory.severity ?? '—')]] }
  if (execution) {
    const completed = Array.isArray(execution.successful_actions) ? execution.successful_actions.length : 0
    const failed = Array.isArray(execution.failed_actions) ? execution.failed_actions.length : 0
    return { mood: failed ? 'alert' : 'success', stage: 'Executing response', headline: failed ? 'One or more actions need attention.' : 'The response plan completed cleanly.', copy: `Sentrix completed ${completed} action${completed === 1 ? '' : 's'}${failed ? ` and recorded ${failed} failure${failed === 1 ? '' : 's'}` : ' with no delivery failures'}.`, metrics: [['Completed', String(completed)], ['Failed', String(failed)]] }
  }
  if (planning) {
    const actions = Array.isArray(planning.actions) ? planning.actions as { kind?: string }[] : []
    return { mood: 'focus', stage: 'Building action plan', headline: `${actions.length} executable action${actions.length === 1 ? '' : 's'} queued.`, copy: actions.length ? `The plan includes ${actions.map(action => String(action.kind ?? 'response').replaceAll('_', ' ')).join(', ')}. These actions come from the agent decision—not a hardcoded alert.` : 'The agent selected monitoring only, so no external notification was added.', metrics: [['Actions', String(actions.length)], ['Source', 'Agent']] }
  }
  if (reasoning) return { mood: 'focus', stage: 'Agent reasoning', headline: `Sentrix classified this as ${String(reasoning.severity ?? 'an assessed')} risk.`, copy: `Groq selected “${String(reasoning.response_action ?? 'monitor')}” after receiving verified evidence, policy context, and the strongest reviewed-memory match.`, metrics: [['Severity', String(reasoning.severity ?? '—')], ['Action', String(reasoning.response_action ?? '—')]] }
  if (retrieval) {
    const policies = Array.isArray(retrieval.evidence) ? retrieval.evidence as { score?: number }[] : []
    const memories = Array.isArray(retrieval.reviewed_incidents) ? retrieval.reviewed_incidents as { similarity?: number }[] : []
    const policyScore = Math.max(0, ...policies.map(item => Number(item.score ?? 0)))
    const memoryScore = Math.max(0, ...memories.map(item => Number(item.similarity ?? 0)))
    return { mood: 'focus', stage: 'Retrieving intelligence', headline: memories.length ? 'A previous reviewed incident may influence this decision.' : 'The policy evidence is ready for reasoning.', copy: `${policies.length} policy chunk${policies.length === 1 ? '' : 's'} retrieved. ${memories.length ? `The strongest human-reviewed match is ${percent(memoryScore)} similar.` : 'No sufficiently similar reviewed incident was found.'}`, metrics: [['Policy', percent(policyScore)], ['Memory', memories.length ? percent(memoryScore) : 'None']] }
  }
  if (verification) {
    const verified = Boolean(verification.verified)
    return { mood: verified ? 'success' : 'alert', stage: 'Verifying candidate', headline: verified ? 'The evidence passed the adaptive gate.' : 'The candidate was suppressed as a likely false alarm.', copy: `The fused risk is ${percent(verification.fused_probability ?? verification.score)} against a learned threshold of ${percent(verification.decision_threshold ?? .68)}.${verification.override_source ? ` A guarded ${String(verification.override_source).replaceAll('_', ' ')} override was applied.` : ''}`, metrics: [['Fused', percent(verification.fused_probability ?? verification.score)], ['Threshold', percent(verification.decision_threshold ?? .68)]] }
  }
  if (detection) return { mood: 'focus', stage: 'Candidate detected', headline: 'The multimodal scan found something worth checking.', copy: `Candidate sources: ${Array.isArray(detection.candidate_sources) ? detection.candidate_sources.join(' + ') : 'visual evidence'}. The raw evidence is moving into statistical verification now.`, metrics: [['Confidence', percent(detection.confidence)], ['Impact', percent(detection.impact_score)]] }
  if (latestFrame || isProcessing) {
    const reading = (name: string) => latestFrame?.readings.find(item => item.sensor_type.toLowerCase().includes(name))?.probability
    const audio = reading('audio')
    const smoke = reading('smoke')
    const visual = reading('visual')
    const frameNumber = latestFrame ? latestFrame.frame_index + 1 : job?.frames_processed ?? 0
    return { mood: 'scan', stage: 'Scanning footage', headline: `Right now we’re reading frame ${frameNumber}.`, copy: `Oh, look—audio is ${audio == null ? 'still arriving' : percent(audio)}, smoke is ${smoke == null ? 'still arriving' : percent(smoke)}${visual == null ? ', while the CV model inspects the image itself.' : `, and visual risk is ${percent(visual)}.`} These values are synchronized before candidate selection.`, metrics: [['Audio', audio == null ? '—' : percent(audio)], ['Smoke', smoke == null ? '—' : percent(smoke)], ['Progress', `${Math.round(job?.progress_percent ?? 0)}%`]] }
  }
  return { mood: 'idle', stage: 'Sentrix guide', headline: 'I’ll explain the evidence as it moves.', copy: 'Upload CCTV footage and run an analysis. I’ll narrate the live sensor values, fusion result, retrieved intelligence, agent decision, actions, and memory—without another API call.', metrics: [['Mode', 'Local'], ['Status', 'Ready']] }
}

export function SentrixGuide({ frames, processingJob, events, isProcessing }: GuideProps) {
  const [minimized, setMinimized] = useState(false)
  const [tourStep, setTourStep] = useState(() => localStorage.getItem('sentrix_workspace_tour_seen') ? -1 : 0)
  const narration = useMemo(() => liveNarration(frames, processingJob, events, isProcessing), [frames, processingJob, events, isProcessing])
  const touring = tourStep >= 0
  const message = touring
    ? { mood: 'focus', eyebrow: tourSteps[tourStep].eyebrow, title: tourSteps[tourStep].title, copy: tourSteps[tourStep].copy, metrics: [] as string[][] }
    : { mood: narration.mood, eyebrow: narration.stage, title: narration.headline, copy: narration.copy, metrics: narration.metrics }

  useEffect(() => {
    document.querySelectorAll('.sentrix-guide-focus').forEach(element => element.classList.remove('sentrix-guide-focus'))
    if (!touring) return
    const target = document.querySelector(tourSteps[tourStep].target)
    target?.classList.add('sentrix-guide-focus')
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return () => target?.classList.remove('sentrix-guide-focus')
  }, [tourStep, touring])

  const finishTour = () => {
    localStorage.setItem('sentrix_workspace_tour_seen', 'true')
    setTourStep(-1)
  }

  const advanceTour = () => {
    if (tourStep === tourSteps.length - 1) finishTour()
    else setTourStep(step => step + 1)
  }

  if (minimized) return <button className="sentrix-guide-minimized" onClick={() => setMinimized(false)} aria-label="Open Sentrix guide"><PixelGuide mood={narration.mood} /><span>{isProcessing ? 'LIVE' : 'GUIDE'}</span></button>

  return <>{touring && <button className="sentrix-tour-click-layer" onClick={advanceTour} aria-label="Continue workspace tour" />}
  <aside className={`sentrix-guide ${touring ? 'is-touring' : ''}`} aria-live="polite" aria-label="Sentrix live guide">
    <div className="sentrix-guide-character"><PixelGuide mood={message.mood} /><div><strong>Sia</strong><span>Sentrix field guide</span></div><i className={isProcessing ? 'live' : ''}>{isProcessing ? 'LIVE' : 'LOCAL'}</i></div>
    <button className="sentrix-guide-minimize" onClick={() => setMinimized(true)} aria-label="Minimize guide">—</button>
    <div className="sentrix-guide-bubble">
      <p>{message.eyebrow}</p>
      <h3>{message.title}</h3>
      <div>{message.copy}</div>
      {!touring && <section>{message.metrics.map(([label, value]) => <span key={label}><small>{label}</small><strong>{value}</strong></span>)}</section>}
    </div>
    {touring ? <footer><button onClick={() => tourStep === 0 ? finishTour() : setTourStep(step => step - 1)}>{tourStep === 0 ? 'Skip' : 'Back'}</button><span>Tap anywhere · {tourStep + 1} / {tourSteps.length}</span><button className="primary" onClick={advanceTour}>{tourStep === tourSteps.length - 1 ? 'Start demo' : 'Next'}</button></footer> : <footer><button onClick={() => { setMinimized(false); setTourStep(0) }}>Replay tour</button><span>NO EXTRA API</span></footer>}
  </aside></>
}

function PixelGuide({ mood }: { mood: string }) {
  const cheek = mood === 'alert' ? '#e25d67' : '#ed8890'
  const eye = mood === 'success' ? '#27765f' : '#174777'
  return <svg className="pixel-guide" viewBox="0 0 64 80" shapeRendering="crispEdges" aria-hidden="true">
    <rect x="22" y="2" width="20" height="4" fill="#192e4b" /><rect x="16" y="6" width="32" height="5" fill="#192e4b" />
    <rect x="11" y="11" width="42" height="8" fill="#243f61" /><rect x="8" y="19" width="48" height="27" fill="#243f61" /><rect x="6" y="27" width="9" height="27" fill="#192e4b" /><rect x="49" y="27" width="9" height="27" fill="#192e4b" />
    <rect x="15" y="18" width="34" height="27" fill="#f2b69d" /><rect x="15" y="18" width="9" height="6" fill="#243f61" /><rect x="40" y="18" width="9" height="6" fill="#243f61" /><rect x="21" y="14" width="22" height="6" fill="#243f61" />
    <rect x="20" y="27" width="8" height="7" fill="#fff7ec" /><rect x="36" y="27" width="8" height="7" fill="#fff7ec" /><rect x="23" y="28" width="4" height="5" fill={eye} /><rect x="37" y="28" width="4" height="5" fill={eye} />
    <rect x="18" y="36" width="5" height="3" fill={cheek} /><rect x="41" y="36" width="5" height="3" fill={cheek} /><rect x="27" y="39" width="10" height="3" fill="#a34e58" /><rect x="29" y="39" width="6" height="1" fill="#fff" />
    <rect x="27" y="45" width="10" height="5" fill="#e7a589" /><rect x="16" y="50" width="32" height="21" fill="#1b5793" /><rect x="21" y="50" width="22" height="6" fill="#dceefa" /><rect x="29" y="52" width="6" height="9" fill="#76b6dc" />
    <rect x="9" y="53" width="7" height="15" fill="#174777" /><rect x="48" y="53" width="7" height="15" fill="#174777" /><rect x="8" y="66" width="8" height="5" fill="#f2b69d" /><rect x="48" y="66" width="8" height="5" fill="#f2b69d" />
    <rect x="20" y="71" width="10" height="9" fill="#163d6b" /><rect x="34" y="71" width="10" height="9" fill="#163d6b" /><rect x="18" y="77" width="12" height="3" fill="#0f2948" /><rect x="34" y="77" width="12" height="3" fill="#0f2948" />
  </svg>
}
