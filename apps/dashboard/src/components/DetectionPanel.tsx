import { useRef, useState } from 'react'

import { Icon } from './Icon'
import type { DetectionInput, ProcessingJob, SensorScenario, VideoAsset } from '../types'
import { LocationMapPicker } from './LocationMapPicker'

const initialDetection: DetectionInput = {
  camera_id: 'CAM-JN-07',
  confidence: 0.94,
  vehicle_count: 2,
  stopped_vehicle: true,
  impact_score: 0.92,
  location: '',
}

interface DetectionPanelProps {
  onDetect: (input: DetectionInput, sensorScenario: SensorScenario) => void
  onUpload: (file: File) => void
  onSensorDownload: (videoId: string) => void
  video: VideoAsset | null
  processingJob: ProcessingJob | null
  disabled: boolean
  isUploading: boolean
  onCancel: () => void
  onRetry: () => void
}

export function DetectionPanel({ onDetect, onUpload, onSensorDownload, video, processingJob, disabled, isUploading, onCancel, onRetry }: DetectionPanelProps) {
  const [detection, setDetection] = useState(initialDetection)
  const [sensorScenario, setSensorScenario] = useState<SensorScenario>('randomized')
  const fileInput = useRef<HTMLInputElement>(null)
  const latestSample = processingJob?.latest_sensor_sample

  return (
    <section className="panel detection-workspace overflow-hidden">
      <input ref={fileInput} className="hidden" type="file" accept="video/mp4,video/quicktime,video/x-msvideo,video/webm" onChange={(event) => { const file = event.target.files?.[0]; if (file) onUpload(file) }} />
      <div className="camera-feed relative aspect-video overflow-hidden">
        {video && <video className="absolute inset-0 size-full object-cover opacity-75" src={video.playback_url} autoPlay muted loop controls aria-label="Uploaded CCTV footage" />}
        {video && <div className="scanline" />}
        {!video && <div className="camera-empty-state"><span><Icon name="camera" /></span><p>Upload CCTV footage</p><small>MP4, MOV, AVI, or WebM · processed by the configured perception model</small><button className="primary-button" disabled={isUploading} onClick={() => fileInput.current?.click()}>{isUploading ? 'Uploading footage…' : 'Choose CCTV video ↗'}</button></div>}
        {processingJob && <div className="absolute inset-x-4 top-14 z-20"><div className="mb-1.5 flex justify-between text-[10px] font-semibold uppercase tracking-wider text-cyan-200"><span>{processingJob.progress_percent >= 100 && processingJob.status === 'running' ? 'Model scan complete · agent response running' : `Model scanning · ${processingJob.frames_processed} frames`}</span><span>{Math.round(processingJob.progress_percent)}%</span></div><div className="h-1 overflow-hidden rounded-full bg-black/50"><div className="h-full rounded-full bg-cyan-300 transition-all duration-300" style={{ width: `${processingJob.progress_percent}%` }} /></div></div>}
        <div className="absolute left-4 top-4 flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full bg-red-500/15 px-2.5 py-1 text-[10px] font-bold tracking-widest text-red-300 ring-1 ring-red-400/25"><span className="size-1.5 animate-pulse rounded-full bg-red-400" /> CCTV INPUT</span>
          <span className="rounded-full bg-black/40 px-2.5 py-1 text-[10px] text-slate-300 ring-1 ring-white/10">{detection.camera_id}</span>
        </div>
        {video && <><div className="vehicle-box left-[22%] top-[48%] h-[25%] w-[31%]"><span>Risk object · 96%</span></div><div className="vehicle-box left-[56%] top-[42%] h-[28%] w-[26%]"><span>Context signal · 91%</span></div></>}
        <div className="absolute bottom-4 left-4 right-4 z-20 flex items-end justify-between">
          <div><p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Camera location</p><p className="mt-1 text-sm font-medium text-white">{detection.location || 'Select a point on the map'}</p></div>
          <div className="flex items-center gap-2">{video && <button className="upload-button" disabled={isUploading} onClick={() => fileInput.current?.click()}>{isUploading ? 'Uploading…' : 'Replace footage'}</button>}<div className="font-mono text-xs text-cyan-300">REC 00:12:48</div></div>
        </div>
      </div>
      <div className={`sensor-upload-deck ${latestSample ? 'attached' : ''}`}>
        <div className="sensor-upload-copy"><span><Icon name="activity" /></span><div><p>Live synthetic sensor twin</p><small>{processingJob?.sensor_scenario ? `${processingJob.sensor_scenario.replaceAll('_', ' ')} · frame ${latestSample ? latestSample.frame_index + 1 : 0} · ${latestSample ? (latestSample.timestamp_ms / 1000).toFixed(2) : '0.00'}s` : video ? 'Smoke and audio readings will be generated for every scanned frame.' : 'Upload footage to generate a unique per-frame smoke and audio stream.'}</small></div></div>
        <div className="sensor-scenario-picker" role="group" aria-label="Synthetic sensor test scenario">
          {([
            ['both_high', 'Both high', 'Smoke ↑ · Audio ↑'],
            ['both_low', 'Both low', 'Smoke ↓ · Audio ↓'],
            ['smoke_high', 'Smoke high', 'Smoke ↑ · Audio ↓'],
            ['audio_high', 'Audio high', 'Smoke ↓ · Audio ↑'],
            ['randomized', 'Randomized', 'Mixed per-frame values'],
          ] as [SensorScenario, string, string][]).map(([value, label, detail]) => <button type="button" key={value} className={sensorScenario === value ? 'selected' : ''} disabled={disabled} onClick={() => setSensorScenario(value)}><strong>{label}</strong><small>{detail}</small></button>)}
        </div>
        {latestSample && <div className="sensor-profile-preview" aria-live="polite">{latestSample.readings.map(sensor => <div key={sensor.sensor_type}><span>{sensor.sensor_type}</span><strong>{Math.round(sensor.probability * 100)}%</strong><i><b style={{ width: `${sensor.probability * 100}%` }} /></i><small>{Math.round(sensor.reliability * 100)}% reliable · {sensor.age_ms}ms old</small></div>)}</div>}
        <button className="upload-button" disabled={!video || processingJob?.status !== 'completed'} onClick={() => video && onSensorDownload(video.video_id)}>{processingJob?.status === 'completed' ? 'Download generated JSON ↓' : processingJob?.status === 'running' ? 'Generating frame stream…' : 'Available after scan'}</button>
      </div>
      <div className="operation-location-map border-t border-white/7 p-4 sm:p-5"><LocationMapPicker compact value={detection.location} onChange={(location) => setDetection(current => ({ ...current, location }))} /></div>
      <div className="grid gap-3 border-t border-white/7 p-4 sm:grid-cols-[1fr_auto] sm:p-5">
        <label className="field-label">Camera ID<input className="field-input" value={detection.camera_id} onChange={(event) => setDetection({ ...detection, camera_id: event.target.value })} /></label>
        <div className="flex self-end gap-2">{processingJob?.status === 'running' && <button className="upload-button" onClick={onCancel}>Cancel</button>}{(processingJob?.status === 'failed' || processingJob?.status === 'cancelled') && <button className="upload-button" onClick={onRetry}>Retry</button>}<button className="primary-button" disabled={disabled || !detection.location} onClick={() => onDetect(detection, sensorScenario)}><Icon name="warning" className="size-4" />{disabled ? video ? 'Scanning footage…' : 'Analyzing…' : video ? 'Scan uploaded footage' : 'Analyze risk signal'}</button></div>
      </div>
    </section>
  )
}
