import type { AnalyticsSummary, Incident, Severity } from '../types'
import { IncidentTable } from './IncidentTable'

const severities: Severity[] = ['critical', 'high', 'medium', 'low']
const barColors: Record<Severity, string> = { critical: 'bg-red-400', high: 'bg-[#244f89]', medium: 'bg-[#6685ae]', low: 'bg-[#b4c3d6]' }

export function HistoryAnalytics({ incidents, analytics }: { incidents: Incident[]; analytics: AnalyticsSummary }) {
  const maximum = Math.max(1, ...severities.map((item) => analytics.by_severity[item] ?? 0))
  const days = dailyCounts(incidents)
  const dayMaximum = Math.max(1, ...days.map((item) => item.count))
  return (
    <div className="dashboard-page space-y-5">
      <div><p className="eyebrow">Historical intelligence</p><h1 className="mt-2 text-2xl font-semibold text-white">Incident history & analytics</h1><p className="mt-1 text-sm text-slate-500">Organization-scoped trends, reports, and complete agent audits.</p></div>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="panel p-5"><h2 className="text-sm font-semibold text-white">Severity distribution</h2><div className="mt-5 space-y-4">{severities.map((severity) => { const count = analytics.by_severity[severity] ?? 0; return <div key={severity}><div className="mb-1.5 flex justify-between text-xs"><span className="capitalize text-slate-400">{severity}</span><span className="font-mono text-slate-300">{count}</span></div><div className="h-2 overflow-hidden rounded-full bg-white/5"><div className={`h-full rounded-full ${barColors[severity]}`} style={{ width: `${count / maximum * 100}%` }} /></div></div> })}</div></section>
        <section className="panel p-5"><h2 className="text-sm font-semibold text-white">Recent daily activity</h2><div className="mt-5 flex h-40 items-end gap-2">{days.map((day) => <div key={day.label} className="flex min-w-0 flex-1 flex-col items-center gap-2"><span className="font-mono text-[10px] text-slate-500">{day.count}</span><div className="analytics-bar w-full rounded-t" style={{ height: `${Math.max(4, day.count / dayMaximum * 110)}px` }} /><span className="truncate text-[9px] text-slate-600">{day.label}</span></div>)}</div></section>
      </div>
      <IncidentTable incidents={incidents} />
    </div>
  )
}

function dailyCounts(incidents: Incident[]) {
  const formatter = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })
  const dates = Array.from({ length: 7 }, (_, offset) => { const date = new Date(); date.setHours(0, 0, 0, 0); date.setDate(date.getDate() - (6 - offset)); return date })
  return dates.map((date) => ({ label: formatter.format(date), count: incidents.filter((incident) => { const stored = new Date(incident.stored_at); return stored.getFullYear() === date.getFullYear() && stored.getMonth() === date.getMonth() && stored.getDate() === date.getDate() }).length }))
}
