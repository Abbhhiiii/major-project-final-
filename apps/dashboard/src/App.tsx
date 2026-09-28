import { useState } from 'react'

import { AccessFlow } from './components/AccessFlow'
import { LandingPage } from './components/LandingPage'
import { DetectionPanel } from './components/DetectionPanel'
import { HistoryAnalytics } from './components/HistoryAnalytics'
import { PolicyManagement } from './components/PolicyManagement'
import { PipelineTracker } from './components/ReasoningPipeline'
import { LiveAnalysisJourney } from './components/LiveAnalysisJourney'
import { SentrixLogo } from './components/SentrixLogo'
import { SentrixGuide } from './components/SentrixGuide'
import { useDashboard } from './hooks/useDashboard'
import { logout } from './api'

export default function App() {
  const [authenticated, setAuthenticated] = useState(
    () => Boolean(localStorage.getItem('sentinel_token') && localStorage.getItem('sentinel_ready')),
  )
  const [accessMode, setAccessMode] = useState<'login' | 'signup' | null>(null)
  if (!authenticated && !accessMode) return <LandingPage onLogin={() => setAccessMode('login')} onGetStarted={() => setAccessMode('signup')} />
  if (!authenticated) return <AccessFlow initialMode={accessMode ?? 'signup'} onBack={() => setAccessMode(null)} onReady={() => { localStorage.setItem('sentinel_ready', 'true'); setAuthenticated(true) }} />
  return <Dashboard />
}

function Dashboard() {
  const [tab, setTab] = useState<'operations' | 'history' | 'policies'>('operations')
  const { incidents, events, liveSensorFrames, isProcessing, isUploading, video, processingJob, error, scanOrSimulate, uploadFootage, cancelScan, retryScan, downloadGeneratedSensors } = useDashboard()

  return (
    <div className="workspace min-h-screen text-slate-300">
      <div className="workspace-glow" />
      <header className="workspace-header relative z-10 border-b backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <SentrixLogo compact tagline />
          <div className="flex items-center gap-3"><nav className="workspace-nav hidden gap-1 sm:flex"><button className={`upload-button ${tab === 'operations' ? 'text-cyan-300' : ''}`} onClick={() => setTab('operations')}>Operations</button><button className={`upload-button ${tab === 'history' ? 'text-cyan-300' : ''}`} onClick={() => setTab('history')}>History & Analytics</button><button className={`upload-button ${tab === 'policies' ? 'text-cyan-300' : ''}`} onClick={() => setTab('policies')}>Policies</button></nav><span className="status-pill status-live"><span className="status-dot" />Online</span><button className="upload-button" onClick={logout}>Logout</button><div className="grid size-8 place-items-center rounded-full bg-slate-800 text-xs font-semibold text-slate-300 ring-1 ring-white/10">AS</div></div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-4 flex gap-2 sm:hidden"><button className="upload-button" onClick={() => setTab('operations')}>Operations</button><button className="upload-button" onClick={() => setTab('history')}>History</button><button className="upload-button" onClick={() => setTab('policies')}>Policies</button></div>

        {tab === 'operations' ? <>
        {error && <div className="mb-5 rounded-xl border border-red-400/20 bg-red-500/8 px-4 py-3 text-sm text-red-300">{error}</div>}
        <div className="operations-layout"><div className="operations-scan"><DetectionPanel onDetect={scanOrSimulate} onUpload={uploadFootage} onSensorDownload={downloadGeneratedSensors} video={video} processingJob={processingJob} disabled={isProcessing} isUploading={isUploading} onCancel={cancelScan} onRetry={retryScan} /></div><aside className="operations-track"><PipelineTracker events={events} isProcessing={isProcessing} error={error} /></aside><div className="operations-response"><LiveAnalysisJourney frames={liveSensorFrames} processingJob={processingJob} events={events} isProcessing={isProcessing} /></div></div>
        </> : tab === 'history' ? <HistoryAnalytics incidents={incidents} /> : <PolicyManagement />}
      </main>
      <SentrixGuide frames={liveSensorFrames} processingJob={processingJob} events={events} isProcessing={isProcessing} />
    </div>
  )
}
