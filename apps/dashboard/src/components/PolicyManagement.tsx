import { useEffect, useState } from 'react'

import { getOnboarding, uploadPolicy } from '../api'
import type { OnboardingSummary } from '../types'

export function PolicyManagement() {
  const [summary, setSummary] = useState<OnboardingSummary | null>(null)
  const [status, setStatus] = useState('')
  useEffect(() => { getOnboarding().then(setSummary).catch(() => setStatus('Could not load organization configuration.')) }, [])
  async function upload(file?: File) {
    if (!file) return
    setStatus('Extracting and indexing policy…')
    try { await uploadPolicy(file); setSummary(await getOnboarding()); setStatus('Policy indexed and ready for retrieval.') } catch (error) { setStatus(error instanceof Error ? error.message : 'Policy upload failed') }
  }
  return <div className="dashboard-page space-y-5"><div><p className="eyebrow">Knowledge control</p><h1 className="mt-2 text-2xl font-semibold text-white">Policies & cameras</h1><p className="mt-1 text-sm text-slate-500">Manage the organization context retrieved before Groq reasoning.</p></div><div className="grid gap-5 lg:grid-cols-2"><section className="panel p-5"><h2 className="text-sm font-semibold text-white">Indexed policy documents</h2><div className="mt-4 space-y-3">{summary?.documents.map((document) => <div key={document.document_id} className="dashboard-list-item rounded-xl p-3"><p className="text-sm font-medium text-slate-200">{document.filename}</p><p className="mt-1 text-xs text-slate-500">{document.page_count} pages · {document.chunk_count} searchable chunks</p></div>)}{summary && !summary.documents.length && <p className="text-sm text-slate-500">No policies indexed.</p>}</div><label className="field-label mt-5">Add or revise policy<input type="file" accept="application/pdf" className="field-input" onChange={(event) => upload(event.target.files?.[0])} /></label>{status && <p className="mt-3 text-xs text-cyan-300">{status}</p>}</section><section className="panel p-5"><h2 className="text-sm font-semibold text-white">Registered cameras</h2><div className="mt-4 space-y-3">{summary?.cameras.map((camera) => <div key={camera.camera_id} className="dashboard-list-item rounded-xl p-3"><p className="text-sm font-medium text-slate-200">{camera.name}</p><p className="mt-1 text-xs text-slate-500">{camera.location} · {camera.camera_id.slice(0, 8)}</p></div>)}</div><div className="organization-card mt-5 rounded-xl p-4 text-xs text-slate-400"><p className="font-medium text-cyan-300">Organization</p><p className="mt-2">{summary?.organization.name}</p><p className="mt-1">Emergency contact: {summary?.organization.emergency_contact || 'Not configured'}</p><p className="mt-1">Preference: {summary?.organization.notification_preference}</p></div></section></div></div>
}
