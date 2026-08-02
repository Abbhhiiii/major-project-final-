import { useState } from 'react'

import type { Incident } from '../types'
import type { AgentAudit, DeliveryRecord } from '../types'
import { downloadIncidentReport, getIncidentAudit, getIncidentDeliveries } from '../api'
import { IncidentDetail } from './IncidentDetail'

const severityStyles = {
  low: 'severity-low', medium: 'severity-medium', high: 'severity-high', critical: 'severity-critical',
}

export function IncidentTable({ incidents }: { incidents: Incident[] }) {
  const [selected, setSelected] = useState<Incident | null>(null)
  const [audit, setAudit] = useState<AgentAudit | null>(null)
  const [deliveries, setDeliveries] = useState<DeliveryRecord[]>([])
  const [error, setError] = useState<string | null>(null)

  async function inspect(incident: Incident) {
    setSelected(incident); setAudit(null); setError(null)
    try {
      const [nextAudit, nextDeliveries] = await Promise.all([getIncidentAudit(incident.incident_id), getIncidentDeliveries(incident.incident_id)])
      setAudit(nextAudit); setDeliveries(nextDeliveries)
    } catch {
      setError('Audit details are unavailable for this older incident.')
    }
  }
  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/7 px-5 py-4">
        <div><p className="eyebrow">Incident memory</p><h2 className="mt-1 text-base font-semibold text-white">Recent events</h2></div>
        <span className="text-xs text-slate-500">{incidents.length} recorded</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[620px] text-left">
          <thead><tr className="text-[10px] uppercase tracking-[0.16em] text-slate-500"><th>Incident</th><th>Location</th><th>Severity</th><th>Time</th><th>Evidence</th></tr></thead>
          <tbody>
            {incidents.map((incident) => <tr key={incident.incident_id}><td><p className="font-mono text-xs text-slate-300">#{incident.incident_id.slice(0, 8)}</p><p className="mt-1 max-w-xs truncate text-xs text-slate-600">{incident.alert_message}</p></td><td className="text-sm text-slate-300">{incident.location}</td><td><span className={`severity ${severityStyles[incident.severity]}`}>{incident.severity}</span></td><td className="text-xs text-slate-500">{new Date(incident.stored_at).toLocaleString()}</td><td><div className="flex gap-3"><button className="text-xs font-semibold text-cyan-400 hover:text-cyan-200" onClick={() => downloadIncidentReport(incident.incident_id)}>PDF ↓</button><button className="text-xs font-semibold text-emerald-400 hover:text-emerald-200" onClick={() => inspect(incident)}>Details</button></div></td></tr>)}
            {!incidents.length && <tr><td colSpan={5} className="py-12 text-center text-sm text-slate-500">No incidents recorded. Run the simulation to create the first event.</td></tr>}
          </tbody>
        </table>
      </div>
      {selected && audit && <IncidentDetail incident={selected} audit={audit} deliveries={deliveries} onClose={() => setSelected(null)} />}
      {selected && !audit && !error && <p className="border-t border-white/7 p-5 text-sm text-slate-500">Loading audit details…</p>}
      {error && <p className="border-t border-red-400/15 p-5 text-sm text-red-300">{error}</p>}
    </section>
  )
}
