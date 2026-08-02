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

export function ReasoningPipeline({ events, isProcessing }: { events: StageEvent[]; isProcessing: boolean }) {
  const completed = new Map(events.map((event) => [event.stage, event]))
  const activeIndex = Math.min(events.length, stages.length - 1)
  const reasoning = completed.get('reasoning')?.payload
  const rationale = (reasoning?.rationale as string[] | undefined) ?? []

  return (
    <section className="panel overflow-hidden" aria-label="Agent reasoning pipeline">
      <div className="flex items-center justify-between border-b border-white/7 px-5 py-4">
        <div>
          <div className="eyebrow"><Icon name="spark" className="size-3.5" /> Agent intelligence</div>
          <h2 className="mt-1 text-base font-semibold text-white">Live reasoning trace</h2>
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
        {reasoning && (
          <div className="mt-4 rounded-xl border border-cyan-300/15 bg-cyan-400/[0.04] p-4" data-testid="live-reasoning-output">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-300">Groq decision output</p>
              <span className="font-mono text-[10px] text-slate-500">{String(reasoning.model ?? '')}</span>
            </div>
            <p className="mt-2 text-sm font-medium text-white">{String(reasoning.alert_message ?? '')}</p>
            <ul className="mt-3 space-y-1.5 text-xs text-slate-400">
              {rationale.map((item) => <li key={item} className="flex gap-2"><span className="text-cyan-400">•</span><span>{item}</span></li>)}
            </ul>
            <p className="mt-3 text-[10px] uppercase tracking-wider text-slate-500">Emergency notification: {reasoning.notify_emergency_services ? 'recommended' : 'not required'}</p>
          </div>
        )}
      </div>
    </section>
  )
}
