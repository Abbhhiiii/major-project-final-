export type Severity = 'low' | 'medium' | 'high' | 'critical'
export type SensorScenario = 'both_high' | 'both_low' | 'smoke_high' | 'audio_high' | 'randomized'

export interface GeoPlace {
  display_name: string
  latitude: number
  longitude: number
  category: string
}

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
  sensor_readings?: { sensor_type: string; probability: number; reliability: number; age_ms: number; source?: string }[]
  candidate_sources?: string[]
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
  source_video_id?: string | null
  frame_timestamp_ms?: number | null
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

export interface SensorFrameSample {
  frame_index: number
  timestamp_ms: number
  readings: {
    sensor_type: string
    probability: number
    reliability: number
    age_ms: number
    source: string
  }[]
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
  sensor_scenario: string
  latest_sensor_sample: SensorFrameSample | null
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
    reviewed_incidents?: {
      incident_id: string
      similarity: number
      reviewed_severity: string
      response_action: string
      false_alarm?: boolean
      reason: string
      reviewed_at?: string
      original_decision?: { severity?: Severity; response_action?: string }
      influence_weight?: number
      match_method?: string
      sensor_matches?: { sensor_type: string; match: number; weight: number }[]
      feature_matches?: {
        key: string
        label: string
        current: number
        previous: number
        match: number
        weight: number
        weighted_match: number
      }[]
    }[]
    evidence: { document_id: string; filename: string; chunk_position: number; score: number; excerpt: string }[]
    procedures: string[]
    contacts: string[]
    policies?: string[]
    preferences?: string[]
    scan_snapshot?: {
      camera_id: string
      confidence: number
      vehicle_count: number
      stopped_vehicle: boolean
      impact_score: number
      location: string
      occurred_at: string
      frame_timestamp_ms?: number | null
      source_video_id?: string | null
      candidate_sources: string[]
      sensor_readings: { sensor_type: string; probability: number; reliability: number; age_ms: number; source: string }[]
      sensor_timeline?: SensorFrameSample[]
      sensor_scenario?: string
    }
    verification_snapshot?: {
      verified: boolean
      score: number
      fused_probability: number
      decision_threshold: number
      forced_accept?: boolean
      base_decision_threshold?: number
      threshold_adjustment?: number
      threshold_minimum?: number
      threshold_maximum?: number
      threshold_stabilizer?: number
      threshold_maximum_adjustment?: number
      default_decision_threshold?: number
      threshold_profile_updated?: boolean
      threshold_new_review_count?: number
      threshold_applied_review_versions?: string[]
      threshold_factors?: {
        incident_id: string
        review_version?: string
        effect: string
        direction: number
        similarity: number
        recency: number
        age_days: number
        weight: number
        signed_weight: number
        reviewed_severity: string
        response_action: string
        reason: string
        already_learned?: boolean
        applied_to_baseline?: boolean
      }[]
      baseline_verified?: boolean
      adaptive_verified?: boolean
      override_source: string | null
      contributions: Record<string, number>
      evidence: string[]
    }
  }
  decision: {
    severity: Severity
    rationale: string[]
    notify_emergency_services: boolean
    alert_message: string
    response_action?: 'call' | 'message' | 'none'
    memory_influence?: {
      applied: boolean
      incident_ids: string[]
      effect: 'raised' | 'lowered' | 'confirmed' | 'none'
      explanation: string
      weight?: number
      current_weight?: number
      base_severity?: Severity
      base_action?: 'call' | 'message' | 'none'
      reviewed_severity?: Severity
      reviewed_action?: 'call' | 'message' | 'none'
      severity_score?: number
      action_score?: number
      method?: string
      reviewed_severity_floor?: Severity
    }
  }
  plan: {
    actions: { kind: string; target: string; message: string; details?: Record<string, unknown> }[]
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
