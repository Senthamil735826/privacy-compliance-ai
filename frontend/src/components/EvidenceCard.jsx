import { useState, Fragment } from 'react'
import { FileText, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react'

/**
 * Safely highlight verified matched terms within text without innerHTML vulnerabilities.
 */
function HighlightedPassage({ text, terms = [] }) {
  if (!text) return null
  if (!terms || terms.length === 0) {
    return <span className="evidence-passage-text">{text}</span>
  }

  // Filter terms to those with length >= 2 and sort by descending length to match longest first
  const cleanTerms = terms
    .filter((t) => typeof t === 'string' && t.trim().length >= 2)
    .sort((a, b) => b.length - a.length)

  if (cleanTerms.length === 0) {
    return <span className="evidence-passage-text">{text}</span>
  }

  // Escape regex special chars
  const regexPattern = new RegExp(
    `(${cleanTerms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi'
  )

  const parts = text.split(regexPattern)

  return (
    <span className="evidence-passage-text">
      {parts.map((part, i) => {
        const isMatch = cleanTerms.some(
          (term) => term.toLowerCase() === part.toLowerCase()
        )
        return isMatch ? (
          <mark key={i} className="evidence-highlight">
            {part}
          </mark>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        )
      })}
    </span>
  )
}

export function EvidenceCard({
  evidenceItem,
  index = 0,
  documentFilename = '',
  showPageNumbers = true,
}) {
  const [copied, setCopied] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  // Extract fields gracefully whether evidenceItem is string or object
  const passageText =
    typeof evidenceItem === 'string' ? evidenceItem : evidenceItem?.text || ''
  const matchedTerms =
    evidenceItem?.matches && Array.isArray(evidenceItem.matches)
      ? evidenceItem.matches
      : []

  const pageNum = evidenceItem?.page || evidenceItem?.page_number || null
  const charSpan =
    evidenceItem?.characters ||
    (evidenceItem?.char_start !== undefined && evidenceItem?.char_end !== undefined
      ? `${evidenceItem.char_start}–${evidenceItem.char_end}`
      : null)

  // Determine if text is long enough for collapse (> 220 chars)
  const isLong = passageText.length > 220

  async function handleCopy() {
    if (!passageText) return
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(passageText)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    } catch (err) {
      console.warn('Clipboard write failed:', err)
    }
  }

  // Construct source provenance line strictly from existing data
  const sourceParts = []
  if (documentFilename) {
    sourceParts.push(`Source: ${documentFilename}`)
  }
  if (showPageNumbers && pageNum !== null) {
    sourceParts.push(`Page ${pageNum}`)
  }
  if (charSpan) {
    sourceParts.push(`Characters ${charSpan}`)
  }

  return (
    <div className="evidence-card">
      <div className="evidence-card-content">
        {/* Left Column: Citation metadata, Quote box, provenance */}
        <div className="evidence-card-main">
          <div className="evidence-card-header">
            <div className="evidence-card-meta-left">
              <FileText size={15} className="evidence-meta-icon" aria-hidden="true" />
              <span className="evidence-number-label">Evidence {index + 1}</span>
              {showPageNumbers && pageNum !== null && (
                <span className="evidence-page-chip">Page {pageNum}</span>
              )}
            </div>

            <div className="evidence-card-actions">
              <button
                type="button"
                className={`evidence-copy-btn ${copied ? 'evidence-copy-btn--copied' : ''}`}
                onClick={handleCopy}
                aria-label={copied ? 'Evidence text copied to clipboard' : 'Copy evidence text'}
                title={copied ? 'Copied!' : 'Copy evidence'}
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied && <span className="evidence-copy-tooltip">Copied</span>}
              </button>
            </div>
          </div>

          {/* Inset Quote Box */}
          <div className="evidence-quote-box">
            <div
              className={`evidence-passage-wrap ${!isExpanded && isLong ? 'evidence-passage-wrap--clamped' : ''}`}
            >
              <HighlightedPassage text={passageText} terms={matchedTerms} />
            </div>

            {isLong && (
              <button
                type="button"
                className="evidence-expand-btn"
                onClick={() => setIsExpanded(!isExpanded)}
                aria-expanded={isExpanded}
              >
                {isExpanded ? (
                  <>
                    <span>Show less</span>
                    <ChevronUp size={13} aria-hidden="true" />
                  </>
                ) : (
                  <>
                    <span>Show more</span>
                    <ChevronDown size={13} aria-hidden="true" />
                  </>
                )}
              </button>
            )}
          </div>

          {/* Provenance source line (only present parts) */}
          {sourceParts.length > 0 && (
            <div className="evidence-source-line">
              <span>{sourceParts.join(' · ')}</span>
            </div>
          )}
        </div>

        {/* Right Column: Matched Terms */}
        <div className="evidence-card-terms">
          <h5 className="matched-terms-heading">Matched Terms</h5>
          {matchedTerms.length > 0 ? (
            <div className="matched-terms-pills">
              {matchedTerms.map((term, tIdx) => (
                <span key={tIdx} className="matched-term-pill">
                  {term}
                </span>
              ))}
            </div>
          ) : (
            <span className="matched-terms-none">No exact keywords tagged</span>
          )}
        </div>
      </div>
    </div>
  )
}
