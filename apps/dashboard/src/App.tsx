import { useState } from 'react'

import { AccessFlow } from './components/AccessFlow'
import { LandingPage } from './components/LandingPage'
import { DetectionPanel } from './components/DetectionPanel'
import { Icon } from './components/Icon'
import { HistoryAnalytics } from './components/HistoryAnalytics'
import { PolicyManagement } from './components/PolicyManagement'
import { AIResponse, PipelineTracker } from './components/ReasoningPipeline'
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
  const { incidents, analytics, events, isProcessing, isUploading, video, processingJob, error, scanOrSimulate, uploadFootage, cancelScan, retryScan } = useDashboard()
  const verified = (analytics.by_severity.high ?? 0) + (analytics.by_severity.critical ?? 0)

  return (
    <div className="workspace min-h-screen text-slate-300">
      <div className="workspace-glow" />
      <header className="workspace-header relative z-10 border-b backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3"><div className="logo-mark"><Icon name="shield" className="size-5" /></div><div><p className="text-sm font-bold tracking-wide text-white">SENTRIX</p><p className="text-[9px] uppercase tracking-[0.24em] text-slate-600">Context-aware surveillance</p></div></div>
          <div className="flex items-center gap-3"><nav className="hidden gap-1 sm:flex"><button className={`upload-button ${tab === 'operations' ? 'text-cyan-300' : ''}`} onClick={() => setTab('operations')}>Operations</button><button className={`upload-button ${tab === 'history' ? 'text-cyan-300' : ''}`} onClick={() => setTab('history')}>History & Analytics</button><button className={`upload-button ${tab === 'policies' ? 'text-cyan-300' : ''}`} onClick={() => setTab('policies')}>Policies</button></nav><span className="status-pill status-live"><span className="status-dot" />Online</span><button className="upload-button" onClick={logout}>Logout</button><div className="grid size-8 place-items-center rounded-full bg-slate-800 text-xs font-semibold text-slate-300 ring-1 ring-white/10">AS</div></div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-4 flex gap-2 sm:hidden"><button className="upload-button" onClick={() => setTab('operations')}>Operations</button><button className="upload-button" onClick={() => setTab('history')}>History</button><button className="upload-button" onClick={() => setTab('policies')}>Policies</button></div>

        {tab === 'operations' ? <>
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="eyebrow"><Icon name="activity" className="size-3.5" /> Operations center</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">Context-aware risk intelligence</h1><p className="mt-1 text-sm text-slate-500">Detection, contextual verification, response, and memory in one live workflow.</p></div><p className="font-mono text-xs text-slate-600">NODE / BENGALURU-01</p></div>

        {error && <div className="mb-5 rounded-xl border border-red-400/20 bg-red-500/8 px-4 py-3 text-sm text-red-300">{error}</div>}

        <div className="workspace-metrics mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric icon="history" label="Total incidents" value={analytics.total_incidents} detail="Stored in local memory" />
          <Metric icon="shield" label="Severe verified" value={verified} detail="High + critical events" accent="cyan" />
          <Metric icon="warning" label="Critical" value={analytics.by_severity.critical ?? 0} detail="Emergency escalation" accent="red" />
          <Metric icon="activity" label="Agent pipeline" value="7/7" detail="All stages operational" accent="green" />
        </div>

        <div className="operations-layout"><div className="operations-scan"><DetectionPanel onDetect={scanOrSimulate} onUpload={uploadFootage} video={video} processingJob={processingJob} disabled={isProcessing} isUploading={isUploading} onCancel={cancelScan} onRetry={retryScan} /></div><aside className="operations-track"><PipelineTracker events={events} isProcessing={isProcessing} /></aside><div className="operations-response"><AIResponse events={events} isProcessing={isProcessing} /></div></div>
        </> : tab === 'history' ? <HistoryAnalytics incidents={incidents} analytics={analytics} /> : <PolicyManagement />}
      </main>
    </div>
  )
}

function Metric({ icon, label, value, detail, accent = 'slate' }: { icon: 'activity' | 'history' | 'shield' | 'warning'; label: string; value: string | number; detail: string; accent?: string }) {
  return <div className="panel metric-card"><div className={`metric-icon metric-${accent}`}><Icon name={icon} className="size-4" /></div><div><p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p><p className="mt-1 text-2xl font-semibold text-white">{value}</p><p className="mt-0.5 text-[11px] text-slate-600">{detail}</p></div></div>
}
