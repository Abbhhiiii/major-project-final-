import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { SentrixGuide } from './SentrixGuide'
import type { ProcessingJob, SensorFrameSample } from '../types'

const job: ProcessingJob = {
  job_id: 'job-1',
  video_id: 'video-1',
  camera_id: 'CAM-01',
  location: 'North gate',
  status: 'running',
  progress_percent: 42,
  frames_processed: 7,
  detections_found: 0,
  sensor_scenario: 'randomized',
  latest_sensor_sample: null,
  error_message: null,
  created_at: '2026-09-28T00:00:00Z',
  updated_at: '2026-09-28T00:00:01Z',
}

const frames: SensorFrameSample[] = [{
  frame_index: 6,
  timestamp_ms: 600,
  readings: [
    { sensor_type: 'audio', probability: .82, reliability: .94, age_ms: 0, source: 'synthetic' },
    { sensor_type: 'smoke', probability: .31, reliability: .91, age_ms: 0, source: 'synthetic' },
  ],
}]

describe('SentrixGuide', () => {
  beforeEach(() => localStorage.clear())

  it('opens with the first-visit workspace tour and advances through it', () => {
    render(<SentrixGuide frames={[]} processingJob={null} events={[]} isProcessing={false} />)
    expect(screen.getByText('Everything has its own room')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Continue workspace tour' }))
    expect(screen.getByText('This is the camera workspace')).toBeInTheDocument()
  })

  it('narrates live frame sensor metrics without another API', () => {
    localStorage.setItem('sentrix_workspace_tour_seen', 'true')
    render(<SentrixGuide frames={frames} processingJob={job} events={[]} isProcessing />)
    expect(screen.getByText('Right now we’re reading frame 7.')).toBeInTheDocument()
    expect(screen.getByText('82%')).toBeInTheDocument()
    expect(screen.getByText('31%')).toBeInTheDocument()
    expect(screen.getByText('NO EXTRA API')).toBeInTheDocument()
  })
})
