import type { Incident } from '../types'
import { IncidentAnalysis } from './IncidentAnalysis'

export function HistoryAnalytics({ incidents }: { incidents: Incident[] }) {
  return <div className="dashboard-page"><IncidentAnalysis incidents={incidents} /></div>
}
