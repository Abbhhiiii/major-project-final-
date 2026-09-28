type SentrixLogoProps = {
  inverse?: boolean
  tagline?: boolean
  compact?: boolean
}

export function SentrixLogo({ inverse = false, tagline = false, compact = false }: SentrixLogoProps) {
  return <span className={`sentrix-logo ${inverse ? 'sentrix-logo-inverse' : ''} ${compact ? 'sentrix-logo-compact' : ''}`}>
    <svg className="sentrix-logo-mark" viewBox="0 0 46 46" fill="none" aria-hidden="true">
      <rect className="camera-top" x="11" y="7" width="15" height="9" rx="4.5" />
      <rect className="camera-body" x="4" y="12" width="38" height="29" rx="9" />
      <circle className="camera-lens-ring" cx="23" cy="26.5" r="9" />
      <circle className="camera-lens" cx="23" cy="26.5" r="5.2" />
      <circle className="camera-glint" cx="20.8" cy="24.3" r="1.6" />
      <circle className="camera-status" cx="36" cy="19" r="2" />
    </svg>
    <span className="sentrix-logo-copy"><strong>Sentrix</strong>{tagline && <small>AI surveillance framework</small>}</span>
  </span>
}
