import { Icon } from './Icon'
import { SentrixLogo } from './SentrixLogo'

type LandingPageProps = {
  onLogin: () => void
  onGetStarted: () => void
}

const features = [
  ['camera', 'Real visual risk detection', 'Uploaded footage is decoded frame by frame and scored by the configured perception model.'],
  ['shield', 'Policy-aware decisions', 'Your uploaded procedures and constraints are retrieved before the agent decides what to do.'],
  ['spark', 'Live agent reasoning', 'Follow every verification, retrieval, decision, and plan as the pipeline moves.'],
  ['activity', 'Temporal verification', 'Evidence across multiple frames helps distinguish real incidents from isolated detections.'],
  ['history', 'Durable incident memory', 'Every decision, action, and outcome is stored in an auditable incident timeline.'],
  ['warning', 'Actionable response', 'Reports and alerts are generated from the agent plan instead of hardcoded templates.'],
] as const

export function LandingPage({ onLogin, onGetStarted }: LandingPageProps) {
  return <div className="landing-page">
    <div className="landing-orb landing-orb-one" /><div className="landing-orb landing-orb-two" />
    <header className="landing-header">
      <a className="landing-brand" href="#top"><SentrixLogo /></a>
      <nav className="landing-nav" aria-label="Main navigation"><a href="#overview">Overview</a><a href="#process">How it works</a><a href="#features">Features</a><button onClick={onLogin}>Log in</button></nav>
      <button className="landing-pill" onClick={onGetStarted}>Get started <span>↗</span></button>
    </header>

    <main id="top">
      <section className="landing-hero" id="overview">
        <p className="landing-kicker landing-reveal">AI surveillance framework</p>
        <h1 className="landing-reveal landing-delay-1">Observe<span>.</span> Understand<span>.</span><br />Respond<span>.</span></h1>
        <p className="landing-hero-copy landing-reveal landing-delay-2">Sentrix is a framework for building context-aware, risk-aware AI surveillance—from multimodal evidence to an explainable response.</p>
        <div className="landing-hero-actions landing-reveal landing-delay-2"><button className="landing-primary" onClick={onGetStarted}>Start monitoring <span>↗</span></button><a href="#process">See how it works <span>↓</span></a></div>
        <div className="landing-divider landing-reveal landing-delay-3"><span /><i><Icon name="spark" /></i><span /></div>
        <div className="landing-product-grid landing-reveal landing-delay-3 landing-opening-cards">
          <article className="product-card product-card-left">
            <div className="product-bar"><span>LIVE CONFIDENCE</span><i>•••</i></div>
            <div className="confidence-ring"><div><strong>89</strong><small>/100</small></div></div>
            <p className="product-title">Elevated risk detected</p><p className="product-muted">Context confirmed across 18 frames</p>
            <div className="signal-row"><span><i className="signal-blue" />Anomaly</span><b>0.92</b></div><div className="signal-row"><span><i />Restricted zone</span><b>0.86</b></div><div className="signal-row"><span><i />Persistence</span><b>0.91</b></div>
          </article>
          <article className="product-card product-card-center">
            <div className="product-bar"><span>RESPONSE PIPELINE</span><em>Live</em></div>
            <div className="mini-video"><span>CAM 07 · NORTH PERIMETER</span><div className="detection-box">RISK SIGNAL · 91%</div><div className="scene-line scene-one"/><div className="scene-line scene-two"/></div>
            <div className="mini-steps"><div className="done"><b>01</b><span>Detection<small>Model evidence received</small></span><strong>✓</strong></div><div className="done"><b>02</b><span>Verification<small>False alarm suppression accepted</small></span><strong>✓</strong></div><div className="active"><b>03</b><span>Policy retrieval<small>Matching emergency procedures</small></span><strong>•••</strong></div></div>
          </article>
          <article className="product-card product-card-right">
            <div className="product-bar"><span>AGENT DECISION</span><i>•••</i></div>
            <div className="agent-badge"><Icon name="spark" /><span>Sentrix agent<small>Reasoning with Groq</small></span></div>
            <div className="chat-bubble">The observed behavior and site context meet the policy threshold for a high-risk event.</div>
            <div className="action-card"><span>Recommended action</span><strong>Notify control room & preserve evidence</strong><small>Based on policy sections 3.2 and 5.1</small></div>
            <button className="mini-button">View complete rationale <span>↗</span></button>
          </article>
        </div>
      </section>

      <section className="landing-section" id="process">
        <p className="section-kicker">One continuous workflow</p><h2>From camera evidence<br />to coordinated action<span>.</span></h2>
        <div className="process-grid"><div><span>01</span><Icon name="camera" /><h3>See the event</h3><p>The configured model scans real frames and returns normalized evidence, confidence, and timestamps.</p></div><div><span>02</span><Icon name="spark" /><h3>Understand the context</h3><p>The agent combines verified evidence with the policies, contacts, and procedures relevant to the site.</p></div><div><span>03</span><Icon name="activity" /><h3>Act with clarity</h3><p>A structured plan drives alerts, reports, dashboard events, and durable incident memory.</p></div></div>
      </section>

      <section className="landing-section feature-section" id="features">
        <p className="section-kicker">Designed for trust</p><h2>Serious intelligence.<br />Completely visible<span>.</span></h2>
        <div className="feature-grid">{features.map(([icon, title, copy]) => <article key={title}><div><Icon name={icon} /></div><h3>{title}</h3><p>{copy}</p><span className="feature-arrow">↗</span></article>)}</div>
      </section>

      <section className="landing-cta"><div><p>Ready when every second matters.</p><h2>Turn surveillance into<br />a response system<span>.</span></h2></div><button onClick={onGetStarted}>Create your workspace <span>↗</span></button><div className="cta-rings" /></section>
    </main>
    <footer className="landing-footer"><a className="landing-brand" href="#top"><SentrixLogo /></a><p>An AI surveillance framework, from evidence to action.</p><button onClick={onLogin}>Operator login ↗</button></footer>
  </div>
}
