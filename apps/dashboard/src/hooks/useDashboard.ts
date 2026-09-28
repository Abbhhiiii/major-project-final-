import { useCallback, useEffect, useState } from 'react'

import { cancelProcessingJob, downloadSensorStream, getAnalytics, getIncidents, observeProcessingJob, retryProcessingJob, startVideoProcessing, streamDetection, uploadVideo } from '../api'
import type { AnalyticsSummary, DetectionInput, Incident, ProcessingJob, SensorFrameSample, SensorScenario, StageEvent, VideoAsset } from '../types'

const emptyAnalytics: AnalyticsSummary = { total_incidents: 0, by_severity: {} }
const DEMO_STAGE_HOLD_MS = 4100

async function loadDashboard() {
  const [history, summary] = await Promise.all([getIncidents(), getAnalytics()])
  return { history, summary }
}

export function useDashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [analytics, setAnalytics] = useState<AnalyticsSummary>(emptyAnalytics)
  const [events, setEvents] = useState<StageEvent[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [video, setVideo] = useState<VideoAsset | null>(null)
  const [processingJob, setProcessingJob] = useState<ProcessingJob | null>(null)
  const [liveSensorFrames, setLiveSensorFrames] = useState<SensorFrameSample[]>([])
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const { history, summary } = await loadDashboard()
    setIncidents(history.items)
    setAnalytics(summary)
  }, [])

  useEffect(() => {
    let active = true
    loadDashboard()
      .then(({ history, summary }) => {
        if (!active) return
        setIncidents(history.items)
        setAnalytics(summary)
      })
      .catch(() => {
        if (active) setError('Backend unavailable. Start FastAPI on port 8000.')
      })
    return () => {
      active = false
    }
  }, [])

  const runDetection = useCallback(
    async (detection: DetectionInput) => {
      setIsProcessing(true)
      setEvents([])
      setLiveSensorFrames([])
      setError(null)
      try {
        await streamDetection(detection, async (event) => {
          setEvents((current) => [...current, event])
          await new Promise((resolve) => window.setTimeout(resolve, DEMO_STAGE_HOLD_MS))
        })
        await refresh()
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Incident processing failed')
      } finally {
        setIsProcessing(false)
      }
    },
    [refresh],
  )

  const uploadFootage = useCallback(async (file: File) => {
    setIsUploading(true)
    setError(null)
    try {
      const asset = await uploadVideo(file)
      setVideo(asset)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Video upload failed')
    } finally {
      setIsUploading(false)
    }
  }, [])

  const scanOrSimulate = useCallback(
    async (detection: DetectionInput, sensorScenario: SensorScenario = 'randomized') => {
      if (!video) {
        await runDetection(detection)
        return
      }
      setIsProcessing(true)
      setEvents([])
      setLiveSensorFrames([])
      setError(null)
      setProcessingJob(null)
      try {
        const queued = await startVideoProcessing(
          video.video_id,
          detection.camera_id,
          detection.location,
          sensorScenario,
        )
        setProcessingJob(queued)
        const finished = await observeProcessingJob(
          queued.job_id,
          setProcessingJob,
          async (event) => {
            setEvents((current) => [...current, event])
            await new Promise((resolve) => window.setTimeout(resolve, DEMO_STAGE_HOLD_MS))
          },
          (sample) => setLiveSensorFrames((current) => current.some((item) => item.frame_index === sample.frame_index) ? current : [...current, sample]),
        )
        if (finished.status === 'failed') {
          throw new Error(finished.error_message ?? 'Video scan failed')
        }
        await refresh()
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Video scan failed')
      } finally {
        setIsProcessing(false)
      }
    },
    [refresh, runDetection, video],
  )

  const cancelScan = useCallback(async () => {
    if (!processingJob) return
    try { setProcessingJob(await cancelProcessingJob(processingJob.job_id)) } catch (caught) { setError(caught instanceof Error ? caught.message : 'Cancellation failed') }
  }, [processingJob])

  const retryScan = useCallback(async () => {
    if (!processingJob) return
    setIsProcessing(true); setEvents([]); setLiveSensorFrames([]); setError(null)
    try {
      const queued = await retryProcessingJob(processingJob.job_id); setProcessingJob(queued)
      const finished = await observeProcessingJob(queued.job_id, setProcessingJob, async (event) => {
        setEvents((current) => [...current, event])
        await new Promise((resolve) => window.setTimeout(resolve, DEMO_STAGE_HOLD_MS))
      }, (sample) => setLiveSensorFrames((current) => current.some((item) => item.frame_index === sample.frame_index) ? current : [...current, sample]))
      if (finished.status === 'failed') throw new Error(finished.error_message ?? 'Video scan failed')
      await refresh()
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Retry failed') } finally { setIsProcessing(false) }
  }, [processingJob, refresh])

  const downloadGeneratedSensors = useCallback(async (videoId: string) => {
    setError(null)
    try {
      await downloadSensorStream(videoId)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sensor stream download failed')
    }
  }, [])

  return {
    incidents,
    analytics,
    events,
    isProcessing,
    isUploading,
    video,
    processingJob,
    liveSensorFrames,
    error,
    scanOrSimulate,
    uploadFootage,
    cancelScan,
    retryScan,
    downloadGeneratedSensors,
  }
}
