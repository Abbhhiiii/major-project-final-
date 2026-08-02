import { Icon } from './Icon'
import type { PipelineStage, StageEvent } from '../types'

const stages: { key: PipelineStage; label: string; short: string }[] = [
  { key: 'detection', label: 'Event received', short: 'CV' },
  { key: 'verification', label: 'Verification', short: 'V' },
  { key: 'context_retrieval', label: 'Policy retrieval', short: 'R' },
  { key: 'reasoning', label: 'Reasoning', short: 'AI' },
  { key: 'planning', label: 'Planning', short: 'P' },
  { key: 'execution', label: 'Execution', short: 'E' },
  { key: 'memory', label: 'Memory', short: 'M' },
]

function detailFor(event?: StageEvent): string {
  if (!event) return 'Waiting for event'
  const payload = event.payload
  if (event.stage === 'verification') return payload.verified ? `Verified · ${Math.round(Number(payload.score) * 100)}%` : 'Suppressed as unverified'
  if (event.stage === 'context_retrieval') {
    const evidence = payload.evidence as { filename: string; score: number }[]
    return evidence?.length ? `${evidence[0].filename} · relevance ${Math.round(evidence[0].score * 100)}%` : `${(payload.policies as unknown[]).length} fallback policy retrieved`
  }
  if (event.stage === 'reasoning') return `${String(payload.severity).toUpperCase()} severity assigned`
  if (event.stage === 'planning') return `${(payload.actions as unknown[]).length} response actions planned`
  if (event.stage === 'execution') return `${(payload.successful_actions as unknown[]).length} actions completed`
  if (event.stage === 'memory') return 'Incident committed to memory'
  return `${String(payload.location)} · ${Math.round(Number(payload.confidence) * 100)}% confidence`
}

function usePipelineState(events: StageEvent[]) {
  const completed = new Map(events.map((event) => [event.stage, event]))
  const activeIndex = Math.min(events.length, stages.length - 1)
  const reasoning = completed.get('reasoning')?.payload
  const rationale = (reasoning?.rationale as string[] | undefined) ?? []
  return { completed, activeIndex, reasoning, rationale }
}

export function PipelineTracker({ events, isProcessing }: { events: StageEvent[]; isProcessing: boolean }) {
  const { completed, activeIndex } = usePipelineState(events)

  return (
    <section className="panel pipeline-tracker overflow-hidden" aria-label="Agent reasoning pipeline">
      <div className="dashboard-card-header flex items-center justify-between px-5 py-4">
        <div>
          <div className="eyebrow"><Icon name="spark" className="size-3.5" /> Agent intelligence</div>
          <h2 className="mt-1 text-base font-semibold text-white">Processing track</h2>
        </div>
        <span className={`status-pill ${isProcessing ? 'status-live' : ''}`}><span className="status-dot" />{isProcessing ? 'Processing' : events.length ? 'Complete' : 'Standby'}</span>
      </div>
      <div className="p-4 sm:p-5">
        <div className="relative space-y-1">
          <div className="absolute bottom-6 left-[19px] top-6 w-px bg-white/8" />
          {stages.map((stage, index) => {
            const event = completed.get(stage.key)
            const isActive = isProcessing && index === activeIndex
            return (
              <div key={stage.key} className={`pipeline-step ${event ? 'pipeline-done' : ''} ${isActive ? 'pipeline-active' : ''}`}>
                <div className="pipeline-node">{event ? '✓' : stage.short}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-slate-200">{stage.label}</p>
                    {event && <span className="text-[10px] font-semibold uppercase tracking-widest text-emerald-400">done</span>}
                  </div>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{detailFor(event)}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export function AIResponse({ events, isProcessing }: { events: StageEvent[]; isProcessing: boolean }) {
  const { reasoning, rationale } = usePipelineState(events)
  return <section className="panel ai-response-card overflow-hidden" aria-label="AI response and decision">
    <div className="dashboard-card-header flex items-center justify-between px-5 py-4">
      <div><div className="eyebrow"><Icon name="spark" className="size-3.5" /> Context-aware response</div><h2 className="mt-1 text-base font-semibold text-white">AI decision & rationale</h2></div>
      <span className={`status-pill ${isProcessing ? 'status-live' : ''}`}><span className="status-dot" />{isProcessing ? 'Reasoning' : reasoning ? 'Decision ready' : 'Awaiting scan'}</span>
    </div>
    <div className="p-5">
      {reasoning ? <div className="ai-response-content" data-testid="live-reasoning-output">
        <div className="ai-agent-line"><span className="ai-agent-avatar"><Icon name="spark" /></span><div><strong>Sentrix agent</strong><small>{String(reasoning.model ?? 'Groq reasoning model')}</small></div><span className="ai-severity">{String(reasoning.severity ?? 'assessed')} risk</span></div>
        <p className="ai-alert-message">{String(reasoning.alert_message ?? '')}</p>
        <div className="ai-rationale-grid">{rationale.map((item, index) => <div key={item}><b>{String(index + 1).padStart(2, '0')}</b><p>{item}</p></div>)}</div>
        <div className="ai-notification"><span>Recommended action</span><strong>{reasoning.notify_emergency_services ? 'Escalate to the configured emergency contact' : 'Continue monitoring under the retrieved policy'}</strong></div>
      </div> : <div className="ai-empty"><span><Icon name="spark" /></span><div><strong>{isProcessing ? 'Building the response…' : 'No decision yet'}</strong><p>{isProcessing ? 'Verified evidence and retrieved policy are being evaluated.' : 'Upload CCTV footage and run a scan to generate a policy-grounded decision.'}</p></div></div>}
    </div>
  </section>
}

export function ReasoningPipeline({ events, isProcessing }: { events: StageEvent[]; isProcessing: boolean }) {
  return <div className="space-y-5"><PipelineTracker events={events} isProcessing={isProcessing} /><AIResponse events={events} isProcessing={isProcessing} /></div>
}
