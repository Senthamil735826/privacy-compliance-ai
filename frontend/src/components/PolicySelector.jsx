import { useState, useRef, useEffect } from 'react'
import { FileText, ChevronDown, Check } from 'lucide-react'

export function PolicySelector({
  activePolicyName,
  policies = [],
  onSelectPolicy,
  isAnalyzed = true,
}) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef(null)

  const hasMultiple = Boolean(policies && policies.length > 1)

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  if (!activePolicyName && (!policies || policies.length === 0)) {
    return (
      <div className="policy-selector-card policy-selector-card--empty">
        <FileText size={16} className="policy-selector-icon" />
        <span className="policy-selector-filename">No Policy Loaded</span>
      </div>
    )
  }

  const displayName = activePolicyName || (policies[0] && policies[0].name) || 'Unnamed Policy'

  return (
    <div className="policy-selector-container" ref={containerRef}>
      <button
        type="button"
        className={`policy-selector-card ${hasMultiple ? 'policy-selector-card--clickable' : ''} ${isOpen ? 'policy-selector-card--open' : ''}`}
        onClick={() => hasMultiple && setIsOpen(!isOpen)}
        aria-haspopup={hasMultiple ? 'listbox' : undefined}
        aria-expanded={hasMultiple ? isOpen : undefined}
        aria-label={hasMultiple ? `Active policy: ${displayName}. Click to switch policy.` : `Active policy: ${displayName}`}
        disabled={!hasMultiple}
      >
        <div className="policy-selector-left">
          <FileText size={16} className="policy-selector-icon" aria-hidden="true" />
          <span className="policy-selector-filename" title={displayName}>
            {displayName}
          </span>
        </div>

        <div className="policy-selector-right">
          {isAnalyzed && (
            <span className="policy-status-pill">
              <span className="policy-status-dot" aria-hidden="true" />
              Analyzed
            </span>
          )}
          {hasMultiple && (
            <ChevronDown
              size={14}
              className={`policy-selector-chevron ${isOpen ? 'policy-selector-chevron--rotated' : ''}`}
              aria-hidden="true"
            />
          )}
        </div>
      </button>

      {hasMultiple && isOpen && (
        <ul className="policy-dropdown-menu" role="listbox" aria-label="Analyzed Policies">
          {policies.map((p) => {
            const isSelected = p.name === displayName
            return (
              <li
                key={p.id || p.name}
                role="option"
                aria-selected={isSelected}
                className={`policy-dropdown-item ${isSelected ? 'policy-dropdown-item--selected' : ''}`}
                onClick={() => {
                  if (onSelectPolicy) onSelectPolicy(p)
                  setIsOpen(false)
                }}
              >
                <div className="policy-dropdown-item-left">
                  <FileText size={14} className="policy-dropdown-item-icon" />
                  <span className="policy-dropdown-item-name">{p.name}</span>
                </div>
                {isSelected && <Check size={14} className="policy-dropdown-item-check" />}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
