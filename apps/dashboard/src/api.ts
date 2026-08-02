import type { AgentAudit, AnalyticsSummary, DeliveryRecord, DetectionInput, IncidentHistory, OnboardingSummary, ProcessingJob, StageEvent, VideoAsset } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
const authHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('sentinel_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { headers: authHeaders() })
  if (response.status === 401) expireLocalSession()
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`)
  return response.json() as Promise<T>
}

function expireLocalSession() {
  localStorage.removeItem('sentinel_token'); localStorage.removeItem('sentinel_ready')
  window.location.reload()
}

export const getIncidents = () => getJson<IncidentHistory>('/api/v1/incidents')
export const getAnalytics = () => getJson<AnalyticsSummary>('/api/v1/analytics/summary')
export const getOnboarding = () => getJson<OnboardingSummary>('/api/v1/onboarding')
export const getIncidentAudit = (incidentId: string) => getJson<AgentAudit>(`/api/v1/incidents/${incidentId}/audit`)
export const getIncidentDeliveries = async (incidentId: string) => {
  const result = await getJson<{ items: DeliveryRecord[] }>(`/api/v1/incidents/${incidentId}/deliveries`)
  return result.items
}

export async function uploadVideo(file: File): Promise<VideoAsset> {
  const body = new FormData()
  body.append('video', file)
  const response = await fetch(`${API_URL}/api/v1/videos`, { method: 'POST', headers: authHeaders(), body })
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(error?.detail ?? `Upload failed with status ${response.status}`)
  }
  const asset = (await response.json()) as Omit<VideoAsset, 'playback_url'>
  return { ...asset, playback_url: URL.createObjectURL(file) }
}

export async function startVideoProcessing(
  videoId: string,
  cameraId: string,
  location: string,
): Promise<ProcessingJob> {
  const response = await fetch(`${API_URL}/api/v1/videos/${videoId}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ camera_id: cameraId, location }),
  })
  if (!response.ok) throw new Error(`Could not start scan (${response.status})`)
  return response.json() as Promise<ProcessingJob>
}

export function observeProcessingJob(
  jobId: string,
  onProgress: (job: ProcessingJob) => void,
  onPipelineEvent: (event: StageEvent) => void,
): Promise<ProcessingJob> {
  return observeAuthenticatedJob(jobId, onProgress, onPipelineEvent)
}

async function observeAuthenticatedJob(jobId: string, onProgress: (job: ProcessingJob) => void, onPipelineEvent: (event: StageEvent) => void): Promise<ProcessingJob> {
  const response = await fetch(`${API_URL}/api/v1/processing-jobs/${jobId}/events`, { headers: { Accept: 'text/event-stream', ...authHeaders() } })
  if (!response.ok || !response.body) throw new Error(`Could not observe scan (${response.status})`)
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  let terminal: ProcessingJob | null = null
  while (true) {
    const { value, done } = await reader.read(); buffer += value ?? ''
    const messages = buffer.split('\n\n'); buffer = messages.pop() ?? ''
    for (const message of messages) {
      const lines = message.split('\n')
      const event = lines.find((line) => line.startsWith('event: '))?.slice(7)
      const data = lines.find((line) => line.startsWith('data: '))?.slice(6)
      if (!data) continue
      if (event === 'pipeline') onPipelineEvent(JSON.parse(data) as StageEvent)
      if (event === 'progress') {
        const job = JSON.parse(data) as ProcessingJob; onProgress(job)
        if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') terminal = job
      }
    }
    if (done) break
  }
  if (!terminal) throw new Error('Scan stream ended without a final status')
  return terminal
}

export async function cancelProcessingJob(jobId: string): Promise<ProcessingJob> {
  const response = await fetch(`${API_URL}/api/v1/processing-jobs/${jobId}/cancel`, { method: 'POST', headers: authHeaders() })
  if (!response.ok) throw new Error('Could not cancel the scan')
  return response.json() as Promise<ProcessingJob>
}

export async function retryProcessingJob(jobId: string): Promise<ProcessingJob> {
  const response = await fetch(`${API_URL}/api/v1/processing-jobs/${jobId}/retry`, { method: 'POST', headers: authHeaders() })
  if (!response.ok) throw new Error('Could not retry the scan')
  return response.json() as Promise<ProcessingJob>
}

export async function downloadIncidentReport(incidentId: string) {
  const response = await fetch(`${API_URL}/api/v1/incidents/${incidentId}/report`, { headers: authHeaders() })
  if (!response.ok) throw new Error('Incident report is unavailable')
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = `incident-${incidentId}.pdf`; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function streamDetection(
  detection: DetectionInput,
  onEvent: (event: StageEvent) => void | Promise<void>,
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/incidents/process/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...authHeaders() },
    body: JSON.stringify(detection),
  })
  if (!response.ok) throw new Error(`Pipeline failed with status ${response.status}`)
  if (!response.body) throw new Error('Streaming is unavailable in this browser')

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += value ?? ''
    const messages = buffer.split('\n\n')
    buffer = messages.pop() ?? ''
    for (const message of messages) {
      const data = message
        .split('\n')
        .find((line) => line.startsWith('data: '))
        ?.slice(6)
      if (data) await onEvent(JSON.parse(data) as StageEvent)
    }
    if (done) break
  }
}

export async function authenticate(mode: 'login' | 'signup', values: Record<string, string>) {
  const response = await fetch(`${API_URL}/api/v1/auth/${mode}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
  })
  const data = await response.json() as { access_token?: string; detail?: string }
  if (!response.ok || !data.access_token) throw new Error(data.detail ?? 'Authentication failed')
  localStorage.setItem('sentinel_token', data.access_token)
}

export async function logout() {
  await fetch(`${API_URL}/api/v1/auth/logout`, { method: 'POST', headers: authHeaders() }).catch(() => undefined)
  expireLocalSession()
}

export async function configureOnboarding(values: Record<string, string>) {
  const response = await fetch(`${API_URL}/api/v1/onboarding`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json', ...authHeaders() }, body: JSON.stringify(values),
  })
  if (!response.ok) throw new Error('Could not save organization setup')
}

export async function uploadPolicy(file: File) {
  const body = new FormData(); body.append('policy', file)
  const response = await fetch(`${API_URL}/api/v1/knowledge/policies`, { method: 'POST', headers: authHeaders(), body })
  const data = await response.json() as { detail?: string }
  if (!response.ok) throw new Error(data.detail ?? 'Policy upload failed')
}
