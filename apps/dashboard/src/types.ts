export type Severity = 'low' | 'medium' | 'high' | 'critical'

export type PipelineStage =
  | 'detection'
  | 'verification'
  | 'context_retrieval'
  | 'reasoning'
  | 'planning'
  | 'execution'
  | 'memory'

export interface DetectionInput {
  camera_id: string
  confidence: number
  vehicle_count: number
  stopped_vehicle: boolean
  impact_score: number
  location: string
  source_video_id?: string
  frame_timestamp_ms?: number
}

export interface StageEvent {
  stage: PipelineStage
  payload: Record<string, unknown>
}

export interface Incident {
  incident_id: string
  detection_id: string
  severity: Severity
  location: string
  rationale: string[]
  alert_message: string
  stored_at: string
}

export interface IncidentHistory {
  items: Incident[]
  count: number
}

export interface AnalyticsSummary {
  total_incidents: number
  by_severity: Partial<Record<Severity, number>>
}

export interface VideoAsset {
  video_id: string
  original_filename: string
  content_type: string
  size_bytes: number
  created_at: string
  playback_path: string
  playback_url: string
}

export interface ProcessingJob {
  job_id: string
  video_id: string
  camera_id: string
  location: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress_percent: number
  frames_processed: number
  detections_found: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface AgentAudit {
  audit_id: string
  incident_id: string
  reasoning_provider: string
  reasoning_model: string
  retrieval: {
    evidence: { filename: string; score: number; excerpt: string }[]
    procedures: string[]
    contacts: string[]
  }
  decision: {
    severity: Severity
    rationale: string[]
    notify_emergency_services: boolean
    alert_message: string
  }
  plan: {
    actions: { kind: string; target: string; message: string }[]
  }
  execution: {
    successful_actions: string[]
    failed_actions: string[]
  }
  created_at: string
}

export interface DeliveryRecord {
  delivery_id: string
  action_kind: string
  target: string
  status: string
  message: string
  provider_reference: string
}

export interface OnboardingSummary {
  organization: { name: string; emergency_contact: string; notification_preference: string }
  cameras: { camera_id: string; name: string; location: string }[]
  documents: { document_id: string; filename: string; page_count: number; chunk_count: number }[]
  onboarding_complete: boolean
}
