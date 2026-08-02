import { useCallback, useEffect, useState } from 'react'

import { cancelProcessingJob, getAnalytics, getIncidents, observeProcessingJob, retryProcessingJob, startVideoProcessing, streamDetection, uploadVideo } from '../api'
import type { AnalyticsSummary, DetectionInput, Incident, ProcessingJob, StageEvent, VideoAsset } from '../types'

const emptyAnalytics: AnalyticsSummary = { total_incidents: 0, by_severity: {} }

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
      setError(null)
      try {
        await streamDetection(detection, async (event) => {
          setEvents((current) => [...current, event])
          await new Promise((resolve) => window.setTimeout(resolve, 320))
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
    async (detection: DetectionInput) => {
      if (!video) {
        await runDetection(detection)
        return
      }
      setIsProcessing(true)
      setEvents([])
      setError(null)
      setProcessingJob(null)
      try {
        const queued = await startVideoProcessing(
          video.video_id,
          detection.camera_id,
          detection.location,
        )
        setProcessingJob(queued)
        const finished = await observeProcessingJob(
          queued.job_id,
          setProcessingJob,
          (event) => setEvents((current) => [...current, event]),
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
    setIsProcessing(true); setEvents([]); setError(null)
    try {
      const queued = await retryProcessingJob(processingJob.job_id); setProcessingJob(queued)
      const finished = await observeProcessingJob(queued.job_id, setProcessingJob, (event) => setEvents((current) => [...current, event]))
      if (finished.status === 'failed') throw new Error(finished.error_message ?? 'Video scan failed')
      await refresh()
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Retry failed') } finally { setIsProcessing(false) }
  }, [processingJob, refresh])

  return {
    incidents,
    analytics,
    events,
    isProcessing,
    isUploading,
    video,
    processingJob,
    error,
    scanOrSimulate,
    uploadFootage,
    cancelScan,
    retryScan,
  }
}
