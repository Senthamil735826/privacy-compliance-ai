
export function BrandLogo({ compact = false, hideText = false, onClick }) {
  return (
    <div
      className={`symbolon-brand ${compact ? 'symbolon-brand--compact' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onClick()
        }
      }}
      title="Symbolon Law — Privacy Intelligence"
    >
      <div className="symbolon-brand-symbol" aria-hidden="true">
        <svg
          width={compact ? '30' : '36'}
          height={compact ? '30' : '36'}
          viewBox="0 0 44 44"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="symbolon-brand-svg"
        >
          {/* Subtle container with rounded corners */}
          <rect width="44" height="44" rx="10" className="brand-svg-bg" />

          {/* Laurel Wreath - Left Branch */}
          <path
            d="M13 32C10 28 9.5 22 11.5 16C12.2 13.8 13.5 11.8 15.5 10.5M11.5 16C10 17.5 9 20 9.5 22.5M12.5 22C11 23.5 10.5 26 11.5 28M14 27.5C13 29.5 13 31.5 14.5 32.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            className="brand-wreath-left"
          />
          {/* Laurel Wreath - Right Branch */}
          <path
            d="M31 32C34 28 34.5 22 32.5 16C31.8 13.8 30.5 11.8 28.5 10.5M32.5 16C34 17.5 35 20 34.5 22.5M31.5 22C33 23.5 33.5 26 32.5 28M30 27.5C31 29.5 31 31.5 29.5 32.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            className="brand-wreath-right"
          />

          {/* Central Pillar of Scales */}
          <line x1="22" y1="12" x2="22" y2="33" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="brand-scales-stem" />
          <path d="M18 33H26" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" className="brand-scales-base" />
          <circle cx="22" cy="11.5" r="2" fill="currentColor" className="brand-scales-finial" />

          {/* Horizontal Beam */}
          <path d="M14 16.5L22 14.5L30 16.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="brand-scales-beam" />

          {/* Left Pan */}
          <path d="M14 16.5L11 23M14 16.5L17 23" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.85" />
          <path d="M10 23.5C10 25.5 18 25.5 18 23.5H10Z" fill="currentColor" className="brand-scales-pan" />

          {/* Right Pan */}
          <path d="M30 16.5L27 23M30 16.5L33 23" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.85" />
          <path d="M26 23.5C26 25.5 34 25.5 34 23.5H26Z" fill="currentColor" className="brand-scales-pan" />
        </svg>
      </div>

      {!hideText && (
        <div className="symbolon-brand-text">
          <div className="symbolon-brand-title">
            <span className="symbolon-brand-name">Symbolon</span>
            <span className="symbolon-brand-tag">LAW</span>
          </div>
          {!compact && (
            <span className="symbolon-brand-subtitle">Privacy Intelligence</span>
          )}
        </div>
      )}
    </div>
  )
}
