import { render, screen } from '@testing-library/react'

import { PipelineTracker, ReasoningPipeline } from './ReasoningPipeline'
import { effectiveReliability, visualProbability } from '../utils/incidentMath'
import { HistoryAnalytics } from './HistoryAnalytics'
import { DetectionPanel } from './DetectionPanel'
import { AdaptiveThresholdVisualization, SensorTimelineVisualization } from './IncidentAnalysis'
import { LiveAnalysisJourney } from './LiveAnalysisJourney'

describe('ReasoningPipeline', () => {
  it('reveals the complete guided live analysis journey from frames through action', () => {
    render(<LiveAnalysisJourney
      frames={[{ frame_index: 0, timestamp_ms: 0, readings: [{ sensor_type: 'smoke', probability: .82, reliability: .95, age_ms: 20, source: 'synthetic_live' }, { sensor_type: 'audio', probability: .78, reliability: .93, age_ms: 30, source: 'synthetic_live' }] }]}
      processingJob={{ job_id: 'job-live', video_id: 'video-live', camera_id: 'cam-live', location: 'Map Point', status: 'completed', progress_percent: 100, frames_processed: 1, detections_found: 1, sensor_scenario: 'both_high', latest_sensor_sample: null, error_message: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }}
      events={[
        { stage: 'detection', payload: { sensor_scenario: 'both_high' } },
        { stage: 'verification', payload: { verified: true, fused_probability: .84, decision_threshold: .68, contributions: { prior: -.4, visual: 1.8 }, evidence: ['Visual and sensor evidence passed.'] } },
        { stage: 'context_retrieval', payload: { evidence: [{ filename: 'policy.pdf', score: .92, excerpt: 'Escalate verified critical events.', chunk_position: 0 }], reviewed_incidents: [{ incident_id: 'prior-1', similarity: .8, reviewed_severity: 'high', response_action: 'call', reason: 'Confirmed by operator.' }] } },
        { stage: 'reasoning', payload: { severity: 'critical', response_action: 'call', alert_message: 'Critical event verified.', rationale: ['Evidence passed verification.'], provider: 'groq', model: 'demo-model' } },
        { stage: 'planning', payload: { actions: [{ kind: 'voice_call', target: 'emergency contact', message: 'Critical event at Map Point.' }] } },
        { stage: 'execution', payload: { successful_actions: ['voice_call'], failed_actions: [] } },
        { stage: 'memory', payload: { incident_id: 'incident-1', severity: 'critical' } },
      ]}
      isProcessing={false}
    />)
    expect(screen.getByText('Frame-by-frame visual and sensor evidence')).toBeInTheDocument()
    expect(screen.getByText('How the fused probability was calculated')).toBeInTheDocument()
    expect(screen.getByText('Policy and previous intelligence retrieved')).toBeInTheDocument()
    expect(screen.getByText('Why the agent selected this response')).toBeInTheDocument()
    expect(screen.getByText('The decision becomes an executable plan')).toBeInTheDocument()
    expect(screen.getByText('Action outcome and durable incident record')).toBeInTheDocument()
  })

  it('shows live generated sensor readings and the post-scan download action', () => {
    render(<DetectionPanel
      onDetect={() => undefined}
      onUpload={() => undefined}
      onSensorDownload={() => undefined}
      video={{ video_id: 'video-1', original_filename: 'demo.mp4', content_type: 'video/mp4', size_bytes: 10, created_at: new Date().toISOString(), playback_path: '/video', playback_url: '/video' }}
      processingJob={{ job_id: 'job-1', video_id: 'video-1', camera_id: 'cam-1', location: 'North Gate', status: 'completed', progress_percent: 100, frames_processed: 30, detections_found: 1, sensor_scenario: 'both_high', latest_sensor_sample: { frame_index: 29, timestamp_ms: 14500, readings: [{ sensor_type: 'smoke', probability: .91, reliability: .96, age_ms: 90, source: 'synthetic_live' }, { sensor_type: 'audio', probability: .88, reliability: .94, age_ms: 60, source: 'synthetic_live' }] }, error_message: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }}
      disabled={false}
      isUploading={false}
      onCancel={() => undefined}
      onRetry={() => undefined}
    />)
    expect(screen.getByText('Live synthetic sensor twin')).toBeInTheDocument()
    expect(screen.getByText('91%')).toBeInTheDocument()
    expect(screen.getByText('Download generated JSON ↓')).toBeInTheDocument()
  })

  it('plots every generated sensor frame in reconstruction', () => {
    render(<SensorTimelineVisualization
      candidateTimestamp={500}
      scenario="audio_high"
      timeline={[
        { frame_index: 0, timestamp_ms: 0, readings: [{ sensor_type: 'smoke', probability: .12, reliability: .93, age_ms: 80, source: 'synthetic_live' }, { sensor_type: 'audio', probability: .2, reliability: .92, age_ms: 70, source: 'synthetic_live' }] },
        { frame_index: 1, timestamp_ms: 500, readings: [{ sensor_type: 'smoke', probability: .14, reliability: .94, age_ms: 70, source: 'synthetic_live' }, { sensor_type: 'audio', probability: .96, reliability: .95, age_ms: 40, source: 'synthetic_live' }] },
      ]}
    />)
    expect(screen.getByTestId('sensor-timeline-visual')).toBeInTheDocument()
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('smoke').length).toBeGreaterThan(0)
    expect(screen.getByText(/audio high/)).toBeInTheDocument()
  })

  it('opens history directly into decision reconstruction', () => {
    render(<HistoryAnalytics incidents={[]} />)
    expect(screen.getByText('Decision reconstruction')).toBeInTheDocument()
    expect(screen.queryByText('Severity distribution')).not.toBeInTheDocument()
    expect(screen.queryByText('Recent daily activity')).not.toBeInTheDocument()
  })

  it('reconstructs the documented visual and freshness mathematics', () => {
    expect(visualProbability(.8, .6)).toBeCloseTo(.73)
    expect(effectiveReliability(.8, 10_000)).toBeCloseTo(.4)
  })

  it('visualizes why reviewed memory changed the verification threshold', () => {
    render(<AdaptiveThresholdVisualization fused={.69} verification={{
      verified: false,
      score: .69,
      fused_probability: .69,
      base_decision_threshold: .68,
      decision_threshold: .6985,
      threshold_adjustment: .0185,
      threshold_minimum: .60,
      threshold_maximum: .76,
      threshold_stabilizer: 3,
      threshold_maximum_adjustment: .08,
      baseline_verified: true,
      adaptive_verified: false,
      override_source: null,
      contributions: {},
      evidence: [],
      threshold_factors: [{
        incident_id: 'previous-incident',
        effect: 'raise_false_alarm',
        direction: 1,
        similarity: .9,
        recency: 1,
        age_days: 0,
        weight: .9,
        signed_weight: .9,
        reviewed_severity: 'low',
        response_action: 'none',
        reason: 'Operator confirmed planned maintenance activity',
      }],
    }} />)
    expect(screen.getByTestId('adaptive-threshold-visual')).toBeInTheDocument()
    expect(screen.getByText('Threshold rose from 68% to 70%')).toBeInTheDocument()
    expect(screen.getByText('#previous')).toBeInTheDocument()
    expect(screen.getByText('Baseline outcome')).toBeInTheDocument()
    expect(screen.getByText('Adaptive outcome')).toBeInTheDocument()
  })
  it('does not label a failed pipeline complete', () => {
    render(<PipelineTracker events={[{ stage: 'verification', payload: { verified: true, score: 0.91 } }]} isProcessing={false} error="Provider failed" />)
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.queryByText('Complete')).not.toBeInTheDocument()
  })

  it('labels a partial pipeline interrupted', () => {
    render(<PipelineTracker events={[{ stage: 'verification', payload: { verified: true, score: 0.91 } }]} isProcessing={false} />)
    expect(screen.getByText('Interrupted')).toBeInTheDocument()
  })

  it('marks completion only after memory', () => {
    render(<PipelineTracker events={[{ stage: 'memory', payload: {} }]} isProcessing={false} />)
    expect(screen.getByText('Complete')).toBeInTheDocument()
  })
  it('shows completed verification evidence and remaining stages', () => {
    render(<ReasoningPipeline events={[{ stage: 'verification', payload: { verified: true, score: 0.91 } }]} isProcessing />)
    expect(screen.getByText('Fused evidence verified · 91%')).toBeInTheDocument()
    expect(screen.getByText('Policy retrieval')).toBeInTheDocument()
    expect(screen.getByText('Processing')).toBeInTheDocument()
  })

  it('renders the live model decision and rationale', () => {
    render(
      <ReasoningPipeline
        events={[{
          stage: 'reasoning',
          payload: {
            severity: 'high',
            alert_message: 'Verified collision at Airport Road.',
            rationale: ['Uploaded policy requires a dashboard alert.'],
            notify_emergency_services: false,
            model: 'openai/gpt-oss-20b',
          },
        }]}
        isProcessing={false}
      />,
    )
    expect(screen.getByTestId('live-reasoning-output')).toBeInTheDocument()
    expect(screen.getByText('Verified collision at Airport Road.')).toBeInTheDocument()
    expect(screen.getByText('Uploaded policy requires a dashboard alert.')).toBeInTheDocument()
  })
})
