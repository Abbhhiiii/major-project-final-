import { useEffect, useState } from 'react'
import { getReview, saveReview } from '../api'

export function IncidentReview({ incidentId, initialSeverity = 'low', initialAction = 'none' }: { incidentId: string; initialSeverity?: string; initialAction?: string }) {
  const [severity, setSeverity] = useState(initialSeverity)
  const [action, setAction] = useState(initialAction)
  const [reason, setReason] = useState('')
  const [falseAlarm, setFalseAlarm] = useState(false)
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(true)
  useEffect(() => {
    let active = true
    getReview(incidentId).then(review => {
      if (!active) return
      if (review) { setSeverity(review.severity); setAction(review.response_action); setReason(review.reason); setFalseAlarm(review.false_alarm); setStatus('Previous review loaded') }
    }).catch(() => { if (active) setStatus('Could not load the review. Reopen details to retry.') }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [incidentId])
  async function persist(nextSeverity = severity, nextAction = action, nextReason = reason, nextFalseAlarm = falseAlarm) {
    setBusy(true)
    try { await saveReview(incidentId, { severity: nextSeverity, response_action: nextAction, reason: nextReason, false_alarm: nextFalseAlarm }); setStatus('Review saved. Similar future incidents will retrieve this judgement.') }
    catch (error) { setStatus(error instanceof Error ? error.message : 'Review failed') }
    finally { setBusy(false) }
  }
  return <form className="panel mt-5 p-5 space-y-3" onSubmit={event => { event.preventDefault(); void persist() }}>
    <h4 className="font-semibold">Was the AI decision appropriate?</h4>
    <p className="text-sm">Approve it directly or correct the severity and response. Either choice becomes reviewed memory for similar future incidents.</p>
    <div className="flex flex-wrap gap-2"><button type="button" disabled={busy} className="primary-button" onClick={() => {
      const approval = 'Operator confirmed the AI rationale, severity, and response were appropriate.'
      setSeverity(initialSeverity); setAction(initialAction); setFalseAlarm(false); setReason(approval)
      void persist(initialSeverity, initialAction, approval, false)
    }}>✓ Decision was appropriate</button><button type="button" className="upload-button" onClick={() => setStatus('Adjust the fields below, explain the correction, then save it.')}>Needs correction</button></div>
    <label className="field-label">Reviewed severity<select className="field-input" value={severity} onChange={event => setSeverity(event.target.value)}>{['low', 'medium', 'high', 'critical'].map(value => <option key={value}>{value}</option>)}</select></label>
    <label className="field-label">Appropriate response<select className="field-input" value={action} onChange={event => setAction(event.target.value)} disabled={falseAlarm}><option value="none">No escalation</option><option value="message">WhatsApp message</option><option value="call">Phone call</option></select></label>
    <label><input type="checkbox" checked={falseAlarm} onChange={event => { setFalseAlarm(event.target.checked); if (event.target.checked) setAction('none') }} /> False alarm</label>
    <label className="field-label">Reason<textarea required minLength={10} maxLength={2000} className="field-input" value={reason} onChange={event => setReason(event.target.value)} /></label>
    <button disabled={busy} className="primary-button">{busy ? 'Please wait…' : 'Save corrected review'}</button>
    <p role="status" className="text-sm">{status}</p>
  </form>
}
