import { FormEvent, useState } from 'react'

import { authenticate, configureOnboarding, uploadPolicy } from '../api'
import { Icon } from './Icon'

export function AccessFlow({ onReady }: { onReady: () => void }) {
  const [mode, setMode] = useState<'login' | 'signup'>('signup')
  const [step, setStep] = useState<'auth' | 'setup'>('auth')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submitAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError('')
    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try { await authenticate(mode, values); if (mode === 'login') onReady(); else setStep('setup') } catch (caught) { setError(caught instanceof Error ? caught.message : 'Authentication failed') } finally { setBusy(false) }
  }

  const submitSetup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    const policy = form.get('policy') as File
    try {
      await configureOnboarding(Object.fromEntries([...form.entries()].filter(([key]) => key !== 'policy')) as Record<string, string>)
      await uploadPolicy(policy)
      onReady()
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Setup failed') } finally { setBusy(false) }
  }

  return <main className="grid min-h-screen place-items-center bg-[#070b12] px-4 py-10 text-slate-300">
    <div className="ambient-glow" />
    <section className="panel relative z-10 w-full max-w-lg overflow-hidden">
      <div className="border-b border-white/7 px-7 py-6"><div className="flex items-center gap-3"><div className="logo-mark"><Icon name="shield" /></div><div><p className="font-bold text-white">SENTINEL <span className="text-cyan-400">AI</span></p><p className="text-[10px] uppercase tracking-[.2em] text-slate-600">Secure organization access</p></div></div></div>
      <div className="p-7">
        <p className="eyebrow">{step === 'auth' ? 'Welcome to the platform' : 'Connect your surveillance site'}</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">{step === 'auth' ? mode === 'signup' ? 'Create your workspace' : 'Sign in to operations' : 'Configure your AI agent'}</h1>
        <p className="mt-2 text-sm text-slate-500">{step === 'auth' ? 'A local demo account keeps your cameras and policies isolated.' : 'Register a camera and upload the policy the agent must follow.'}</p>
        {error && <div className="mt-5 rounded-lg border border-red-400/20 bg-red-400/8 px-3 py-2 text-sm text-red-300">{error}</div>}
        {step === 'auth' ? <form className="mt-6 space-y-4" onSubmit={submitAuth}>
          {mode === 'signup' && <Field label="Organization name" name="organization_name" placeholder="Metro Safety Lab" />}
          <Field label="Email" name="email" type="email" placeholder="operator@example.com" />
          <Field label="Password" name="password" type="password" placeholder="Minimum 8 characters" />
          <button className="primary-button w-full" disabled={busy}>{busy ? 'Please wait…' : mode === 'signup' ? 'Create workspace' : 'Sign in'}</button>
          <button type="button" className="w-full text-xs text-slate-500 hover:text-cyan-300" onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}>{mode === 'signup' ? 'Already registered? Sign in' : 'Need a workspace? Sign up'}</button>
        </form> : <form className="mt-6 grid gap-4 sm:grid-cols-2" onSubmit={submitSetup}>
          <Field label="Camera name" name="camera_name" placeholder="Junction Camera 7" /><Field label="Camera location" name="camera_location" placeholder="Airport Road" />
          <Field label="Emergency contact" name="emergency_contact" placeholder="+91 00000 00000" /><Field label="Mock agent API key" name="agent_api_key" type="password" placeholder="sk-demo-••••••••" />
          <input type="hidden" name="notification_preference" value="voice alert for high-severity incidents" />
          <label className="field-label sm:col-span-2">Policy PDF<input required name="policy" type="file" accept="application/pdf" className="field-input file:mr-3 file:rounded file:border-0 file:bg-cyan-300/10 file:px-2 file:py-1 file:text-xs file:text-cyan-300" /></label>
          <button className="primary-button sm:col-span-2" disabled={busy}>{busy ? 'Reading policy…' : 'Finish setup and open dashboard'}</button>
        </form>}
      </div>
    </section>
  </main>
}

function Field({ label, name, type = 'text', placeholder }: { label: string; name: string; type?: string; placeholder: string }) {
  return <label className="field-label">{label}<input required className="field-input" name={name} type={type} placeholder={placeholder} /></label>
}
