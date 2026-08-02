import type { AgentAudit, DeliveryRecord, Incident } from '../types'
import { downloadIncidentReport } from '../api'

export function IncidentDetail({ incident, audit, deliveries, onClose }: { incident: Incident; audit: AgentAudit; deliveries: DeliveryRecord[]; onClose: () => void }) {
  return (
    <div className="border-t border-white/7 bg-black/15 p-5" data-testid="incident-detail">
      <div className="flex items-start justify-between gap-4">
        <div><p className="eyebrow">Agent audit · #{incident.incident_id.slice(0, 8)}</p><h3 className="mt-2 text-lg font-semibold text-white">{audit.decision.alert_message}</h3><p className="mt-1 font-mono text-[10px] text-slate-500">{audit.reasoning_provider} / {audit.reasoning_model}</p></div>
        <button className="upload-button" onClick={onClose}>Close</button>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <AuditSection title="Reasoning">
          <ul className="space-y-2 text-xs text-slate-400">{audit.decision.rationale.map((item) => <li key={item} className="flex gap-2"><span className="text-cyan-400">•</span><span>{item}</span></li>)}</ul>
        </AuditSection>
        <AuditSection title="Retrieved policy evidence">
          <div className="space-y-3">{audit.retrieval.evidence.map((item) => <div key={`${item.filename}-${item.score}`}><div className="flex justify-between gap-3 text-xs"><span className="font-medium text-slate-200">{item.filename}</span><span className="font-mono text-emerald-400">{Math.round(item.score * 100)}%</span></div><p className="mt-1 text-xs text-slate-500">{item.excerpt.slice(0, 320)}{item.excerpt.length > 320 ? '…' : ''}</p></div>)}{!audit.retrieval.evidence.length && <p className="text-xs text-slate-500">No document evidence was retrieved.</p>}</div>
        </AuditSection>
        <AuditSection title="Planned actions">
          <div className="space-y-2">{audit.plan.actions.map((action) => <div key={`${action.kind}-${action.target}`} className="rounded-lg border border-white/7 bg-white/[0.02] px-3 py-2"><p className="text-xs font-medium text-slate-200">{action.kind.replaceAll('_', ' ')}</p><p className="mt-0.5 text-[11px] text-slate-500">Target: {action.target}</p></div>)}</div>
        </AuditSection>
        <AuditSection title="Execution and report">
          <div className="space-y-2">{deliveries.map((delivery) => <div key={delivery.delivery_id} className="flex items-center justify-between gap-3 text-xs"><span className="text-slate-300">{delivery.action_kind.replaceAll('_', ' ')}</span><span className={delivery.status === 'delivered' ? 'text-emerald-400' : 'text-red-400'}>{delivery.status}</span></div>)}</div>
          <button className="mt-4 text-xs font-semibold text-cyan-400 hover:text-cyan-200" onClick={() => downloadIncidentReport(incident.incident_id)}>Download incident PDF ↓</button>
        </AuditSection>
      </div>
    </div>
  )
}

function AuditSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border border-white/7 bg-[#0b111b] p-4"><h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</h4>{children}</section>
}
