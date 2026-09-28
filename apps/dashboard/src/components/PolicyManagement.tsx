import { FormEvent, useEffect, useState } from 'react'

import { getOnboarding, updateEmergencyContact, uploadPolicy } from '../api'
import type { OnboardingSummary } from '../types'

export function PolicyManagement() {
  const [summary, setSummary] = useState<OnboardingSummary | null>(null)
  const [status, setStatus] = useState('')
  const [contact, setContact] = useState('')
  useEffect(() => {
    getOnboarding().then((data) => {
      setSummary(data)
      setContact(data.organization.emergency_contact)
    }).catch(() => setStatus('Could not load organization configuration.'))
  }, [])
  async function upload(file?: File) {
    if (!file) return
    setStatus('Extracting and indexing policy…')
    try { await uploadPolicy(file); setSummary(await getOnboarding()); setStatus('Policy indexed and ready for retrieval.') } catch (error) { setStatus(error instanceof Error ? error.message : 'Policy upload failed') }
  }
  async function saveContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus('Saving emergency delivery contact…')
    try {
      const updated = await updateEmergencyContact(contact, 'WhatsApp alerts for verified incidents')
      setSummary(updated)
      setContact(updated.organization.emergency_contact)
      setStatus('Emergency contact saved and ready for retrieval.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not save emergency contact')
    }
  }
  return <div className="dashboard-page space-y-5"><div><p className="eyebrow">Knowledge control</p><h1 className="mt-2 text-2xl font-semibold text-white">Policies & cameras</h1><p className="mt-1 text-sm text-slate-500">Manage the organization context retrieved before Groq reasoning.</p></div><div className="grid gap-5 lg:grid-cols-2"><section className="panel p-5"><h2 className="text-sm font-semibold text-white">Indexed policy documents</h2><div className="mt-4 space-y-3">{summary?.documents.map((document) => <div key={document.document_id} className="dashboard-list-item rounded-xl p-3"><p className="text-sm font-medium text-slate-200">{document.filename}</p><p className="mt-1 text-xs text-slate-500">{document.page_count} pages · {document.chunk_count} searchable chunks</p></div>)}{summary && !summary.documents.length && <p className="text-sm text-slate-500">No policies indexed.</p>}</div><label className="field-label mt-5">Add or revise policy<input type="file" accept="application/pdf" className="field-input" onChange={(event) => upload(event.target.files?.[0])} /></label>{status && <p className="mt-3 text-xs text-cyan-300">{status}</p>}</section><section className="panel p-5"><h2 className="text-sm font-semibold text-white">Registered cameras</h2><div className="mt-4 space-y-3">{summary?.cameras.map((camera) => <div key={camera.camera_id} className="dashboard-list-item rounded-xl p-3"><p className="text-sm font-medium text-slate-200">{camera.name}</p><p className="mt-1 text-xs text-slate-500">{camera.location} · {camera.camera_id.slice(0, 8)}</p></div>)}</div><div className="organization-card mt-5 rounded-xl p-4 text-xs text-slate-400"><p className="font-medium text-cyan-300">Organization</p><p className="mt-2">{summary?.organization.name}</p><p className="mt-1">Preference: {summary?.organization.notification_preference}</p></div><form className="organization-card mt-4 rounded-xl p-4" onSubmit={saveContact}><p className="text-xs font-semibold text-cyan-300">Emergency delivery</p><p className="mt-1 text-xs text-slate-500">This organization-wide contact is retrieved before every Groq decision.</p><label className="field-label mt-4">WhatsApp emergency contact<input className="field-input" value={contact} onChange={(event) => setContact(event.target.value)} placeholder="+919876543210" required /></label><button className="primary-button mt-3 px-4 py-2 text-xs" type="submit">Save contact</button></form></section></div></div>
}
