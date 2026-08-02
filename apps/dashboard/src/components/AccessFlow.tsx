import { FormEvent, useState } from 'react'

import { authenticate, configureOnboarding, uploadPolicy } from '../api'
import { Icon } from './Icon'

export function AccessFlow({ initialMode = 'signup', onBack, onReady }: { initialMode?: 'login' | 'signup'; onBack: () => void; onReady: () => void }) {
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode)
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

  return <main className="access-page">
    <button className="access-back" onClick={onBack}>← Back to home</button>
    <section className="access-shell">
      <aside className="access-story"><div className="access-brand"><span><Icon name="shield" /></span>Sentrix</div><div><p>Context to action</p><h2>Every signal.<br />One clear response<span>.</span></h2><div className="access-pipeline"><div className="complete"><b>01</b><span>Detect risk signal</span><i>✓</i></div><div className="complete"><b>02</b><span>Verify context</span><i>✓</i></div><div className="current"><b>03</b><span>Apply policy</span><i>•••</i></div><div><b>04</b><span>Coordinate action</span><i>○</i></div></div></div><small>Context-aware · Risk-aware · Auditable</small></aside>
      <div className="access-form-wrap">
        <div className="access-mobile-brand"><span><Icon name="shield" /></span>Sentrix</div>
        <p className="access-kicker">{step === 'auth' ? 'Secure operator access' : 'One final step'}</p>
        <h1>{step === 'auth' ? mode === 'signup' ? 'Create your workspace.' : 'Welcome back.' : 'Connect your site.'}</h1>
        <p className="access-copy">{step === 'auth' ? mode === 'signup' ? 'Set up a private workspace for your cameras, policies, and incident response.' : 'Sign in to continue to your operations center.' : 'Register a camera and upload the policy your agent must follow.'}</p>
        {error && <div className="mt-5 rounded-lg border border-red-400/20 bg-red-400/8 px-3 py-2 text-sm text-red-300">{error}</div>}
        {step === 'auth' ? <form className="access-form" onSubmit={submitAuth}>
          {mode === 'signup' && <Field label="Organization name" name="organization_name" placeholder="Metro Safety Lab" />}
          <Field label="Email" name="email" type="email" placeholder="operator@example.com" />
          <Field label="Password" name="password" type="password" placeholder="Minimum 8 characters" />
          <button className="access-submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'signup' ? 'Create workspace ↗' : 'Sign in ↗'}</button>
          <button type="button" className="access-switch" onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}>{mode === 'signup' ? 'Already registered? Sign in' : 'New to Sentrix? Create a workspace'}</button>
        </form> : <form className="access-form access-setup" onSubmit={submitSetup}>
          <Field label="Camera name" name="camera_name" placeholder="Perimeter Camera 7" /><Field label="Camera location" name="camera_location" placeholder="North perimeter" />
          <Field label="Emergency contact" name="emergency_contact" placeholder="+91 00000 00000" /><Field label="Mock agent API key" name="agent_api_key" type="password" placeholder="sk-demo-••••••••" />
          <input type="hidden" name="notification_preference" value="voice alert for high-severity incidents" />
          <label className="field-label access-span">Policy PDF<input required name="policy" type="file" accept="application/pdf" className="field-input" /></label>
          <button className="access-submit access-span" disabled={busy}>{busy ? 'Reading policy…' : 'Finish setup and open dashboard ↗'}</button>
        </form>}
      </div>
    </section>
  </main>
}

function Field({ label, name, type = 'text', placeholder }: { label: string; name: string; type?: string; placeholder: string }) {
  return <label className="field-label">{label}<input required className="field-input" name={name} type={type} placeholder={placeholder} /></label>
}
