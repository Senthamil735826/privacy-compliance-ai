import React, { useMemo, useState } from 'react'
import {
  ShieldCheck,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Sparkles,
  ChevronRight,
  X,
  ExternalLink,
  Info,
} from 'lucide-react'
import { StatusBadge } from '../components/StatusBadge'
import { PRIMARY_CATEGORIES, SECONDARY_INDICATORS } from '../data/indicatorsData'

export function IndicatorExplorerView({
  analysis,
  onNavigate,
  onSelectIndicatorForEvidence,
  onSelectIndicatorForAgent,
}) {
  const [selectedPrimary, setSelectedPrimary] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL') // ALL, FOUND, MISSING
  const [searchQuery, setSearchQuery] = useState('')
  const [activeIndicator, setActiveIndicator] = useState(null)

  // Map analysis results by indicator ID (B1-B40)
  const analysisMap = useMemo(() => {
    const map = new Map()
    if (analysis?.indicators) {
      for (const ind of analysis.indicators) {
        map.set(ind.id, ind)
      }
    }
    return map
  }, [analysis])

  const hasAnalysis = Boolean(analysis && analysis.indicators?.length)

  // Merge static metadata with dynamic analysis
  const mergedIndicators = useMemo(() => {
    return SECONDARY_INDICATORS.map((sec) => {
      const result = analysisMap.get(sec.id)
      const isMatched = result ? Boolean(result.matched) : false
      const evidence = result?.evidence || []
      const primaryCat = PRIMARY_CATEGORIES.find((p) => p.id === sec.primary)

      return {
        ...sec,
        primaryName: primaryCat?.name || sec.primary,
        primaryShort: primaryCat?.shortName || sec.primary,
        matched: isMatched,
        hasEvidence: evidence.length > 0,
        evidence: evidence,
        analyzed: hasAnalysis,
      }
    })
  }, [analysisMap, hasAnalysis])

  // Filtered indicators based on category, status, and search query
  const filteredIndicators = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()

    return mergedIndicators.filter((item) => {
      // Primary category filter
      if (selectedPrimary !== 'ALL' && item.primary !== selectedPrimary) {
        return false
      }

      // Status filter
      if (statusFilter === 'FOUND' && (!hasAnalysis || !item.matched)) {
        return false
      }
      if (statusFilter === 'MISSING' && (!hasAnalysis || item.matched)) {
        return false
      }

      // Search query
      if (query) {
        const inId = item.id.toLowerCase().includes(query)
        const inName = item.name.toLowerCase().includes(query)
        const inDesc = item.description.toLowerCase().includes(query)
        const inPrimary = item.primaryName.toLowerCase().includes(query)
        if (!inId && !inName && !inDesc && !inPrimary) {
          return false
        }
      }

      return true
    })
  }, [mergedIndicators, selectedPrimary, statusFilter, searchQuery, hasAnalysis])

  // Compute category statistics
  const primaryStats = useMemo(() => {
    return PRIMARY_CATEGORIES.map((cat) => {
      const items = mergedIndicators.filter((ind) => ind.primary === cat.id)
      const matchedCount = items.filter((ind) => ind.matched).length
      return {
        ...cat,
        total: items.length,
        matched: matchedCount,
        rate: items.length > 0 ? Math.round((matchedCount / items.length) * 100) : 0,
      }
    })
  }, [mergedIndicators])

  return (
    <div className="view-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div className="page-badge">Compliance Framework</div>
          <h1 className="page-title">Indicator Explorer</h1>
          <p className="page-subtitle">
            Explore 40 statutory compliance indicators structured across 7 primary categories.
            Inspect evidence citations and compliance gap findings.
          </p>
        </div>
        {!hasAnalysis && (
          <div className="header-status-note">
            <Info size={16} />
            <span>Showing baseline indicator framework. Analyze a policy to view detection status.</span>
          </div>
        )}
      </div>

      {/* Primary Category Selector Pills (Horizontally scrollable with touch momentum) */}
      <div className="category-pill-selector">
        <button
          type="button"
          className={`category-pill ${selectedPrimary === 'ALL' ? 'category-pill--active' : ''}`}
          onClick={() => setSelectedPrimary('ALL')}
        >
          <span className="category-pill-name">All Categories</span>
          <span className="category-pill-badge">{mergedIndicators.length}</span>
        </button>

        {primaryStats.map((cat) => {
          const isActive = selectedPrimary === cat.id
          return (
            <button
              key={cat.id}
              type="button"
              className={`category-pill ${isActive ? 'category-pill--active' : ''}`}
              onClick={() => setSelectedPrimary(cat.id)}
            >
              <span className="category-pill-id">{cat.id}</span>
              <span className="category-pill-name">{cat.shortName}</span>
              {hasAnalysis ? (
                <span className="category-pill-badge">
                  {cat.matched}/{cat.total}
                </span>
              ) : (
                <span className="category-pill-badge">{cat.total}</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Search & Status Filters Bar */}
      <div className="table-controls-bar card">
        <div className="search-input-wrapper">
          <Search size={16} className="search-input-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search indicator by ID (e.g. B7), name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="filter-button-group">
          <button
            type="button"
            className={`filter-btn ${statusFilter === 'ALL' ? 'filter-btn--active' : ''}`}
            onClick={() => setStatusFilter('ALL')}
          >
            All ({filteredIndicators.length})
          </button>
          <button
            type="button"
            className={`filter-btn ${statusFilter === 'FOUND' ? 'filter-btn--active' : ''}`}
            onClick={() => setStatusFilter('FOUND')}
          >
            Detected
          </button>
          <button
            type="button"
            className={`filter-btn ${statusFilter === 'MISSING' ? 'filter-btn--active' : ''}`}
            onClick={() => setStatusFilter('MISSING')}
          >
            Not Found
          </button>
        </div>
      </div>

      {/* Mobile Card-Based Indicator List (< 768px) */}
      <div className="indicator-mobile-card-list">
        {filteredIndicators.length === 0 ? (
          <div className="card overview-empty-state">
            <Search size={28} className="table-empty-icon" />
            <p>No indicators match the selected criteria.</p>
            <button
              type="button"
              className="btn btn--outline-sm"
              onClick={() => {
                setSelectedPrimary('ALL')
                setStatusFilter('ALL')
                setSearchQuery('')
              }}
            >
              Reset Filters
            </button>
          </div>
        ) : (
          filteredIndicators.map((indicator) => {
            const isSelected = activeIndicator?.id === indicator.id
            return (
              <div
                key={indicator.id}
                className={`card indicator-mobile-card ${isSelected ? 'indicator-mobile-card--selected' : ''}`}
                onClick={() => setActiveIndicator(indicator)}
                role="button"
                tabIndex={0}
              >
                <div className="mobile-card-top">
                  <div className="mobile-card-id-group">
                    <span className="indicator-id-badge">{indicator.id}</span>
                    <span className="indicator-category-tag">{indicator.primary}</span>
                  </div>
                  <div>
                    {hasAnalysis ? (
                      indicator.matched ? (
                        <StatusBadge status="detected" label="Detected" size="small" />
                      ) : (
                        <StatusBadge status="not_found" label="Not Found" size="small" />
                      )
                    ) : (
                      <span className="status-badge status-badge--neutral status-badge--small">
                        Pending
                      </span>
                    )}
                  </div>
                </div>

                <h4 className="mobile-card-title">{indicator.name}</h4>
                <p className="mobile-card-desc">{indicator.description}</p>

                <div className="mobile-card-footer">
                  {indicator.hasEvidence ? (
                    <span className="evidence-count-badge">
                      <FileText size={12} />
                      <span>{indicator.evidence.length} excerpts</span>
                    </span>
                  ) : (
                    <span className="text-muted-sm">No citations</span>
                  )}
                  <button
                    type="button"
                    className="btn btn--outline-sm btn--inspect-mobile"
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveIndicator(indicator)
                    }}
                  >
                    <span>Inspect</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Desktop Responsive Table (>= 768px) */}
      <div className="card table-card indicator-desktop-table">
        <div className="table-responsive">
          <table className="symbolon-table">
            <thead>
              <tr>
                <th style={{ width: '85px' }}>ID</th>
                <th style={{ minWidth: '220px' }}>Indicator Name</th>
                <th style={{ minWidth: '180px' }}>Primary Category</th>
                <th style={{ width: '130px' }}>Status</th>
                <th style={{ width: '130px' }}>Evidence</th>
                <th style={{ width: '100px', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredIndicators.length === 0 ? (
                <tr>
                  <td colSpan={6} className="table-empty-row">
                    <div className="table-empty-content">
                      <Search size={28} className="table-empty-icon" />
                      <p>No indicators match the selected criteria.</p>
                      <button
                        type="button"
                        className="btn btn--outline-sm"
                        onClick={() => {
                          setSelectedPrimary('ALL')
                          setStatusFilter('ALL')
                          setSearchQuery('')
                        }}
                      >
                        Reset Filters
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredIndicators.map((indicator) => {
                  const isSelected = activeIndicator?.id === indicator.id
                  return (
                    <tr
                      key={indicator.id}
                      className={`table-row-hover ${isSelected ? 'table-row--selected' : ''}`}
                      onClick={() => setActiveIndicator(indicator)}
                    >
                      <td>
                        <span className="indicator-id-badge">{indicator.id}</span>
                      </td>
                      <td>
                        <div className="indicator-name-cell">
                          <span className="indicator-name-primary">{indicator.name}</span>
                          <span className="indicator-desc-preview">{indicator.description}</span>
                        </div>
                      </td>
                      <td>
                        <span className="indicator-category-tag">
                          {indicator.primary} • {indicator.primaryShort}
                        </span>
                      </td>
                      <td>
                        {hasAnalysis ? (
                          indicator.matched ? (
                            <StatusBadge status="detected" label="Detected" size="small" />
                          ) : (
                            <StatusBadge status="not_found" label="Not Found" size="small" />
                          )
                        ) : (
                          <span className="status-badge status-badge--neutral status-badge--small">
                            Pending Audit
                          </span>
                        )}
                      </td>
                      <td>
                        {indicator.hasEvidence ? (
                          <span className="evidence-count-badge">
                            <FileText size={12} />
                            <span>{indicator.evidence.length} excerpts</span>
                          </span>
                        ) : (
                          <span className="text-muted-sm">None</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          type="button"
                          className="btn-inspect-row"
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveIndicator(indicator)
                          }}
                        >
                          <span>Inspect</span>
                          <ChevronRight size={14} />
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slide-over Indicator Detail Panel (Adapts to full-width drawer on mobile) */}
      {activeIndicator && (
        <div className="detail-modal-overlay" onClick={() => setActiveIndicator(null)}>
          <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
            <div className="detail-panel-header">
              <div className="detail-panel-title-group">
                <span className="indicator-id-badge indicator-id-badge--lg">
                  {activeIndicator.id}
                </span>
                <div>
                  <h3 className="detail-panel-title">{activeIndicator.name}</h3>
                  <span className="detail-panel-category">
                    {activeIndicator.primary} — {activeIndicator.primaryName}
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="btn-close-panel"
                onClick={() => setActiveIndicator(null)}
                aria-label="Close detail panel"
              >
                <X size={20} />
              </button>
            </div>

            <div className="detail-panel-body">
              {/* Statutory Definition */}
              <div className="detail-section">
                <h4 className="detail-section-heading">Statutory Requirement & Purpose</h4>
                <div className="detail-definition-box">
                  <p>{activeIndicator.description}</p>
                </div>
              </div>

              {/* Audit Status */}
              <div className="detail-section">
                <h4 className="detail-section-heading">Document Finding</h4>
                <div className="detail-status-row">
                  {hasAnalysis ? (
                    activeIndicator.matched ? (
                      <div className="status-banner status-banner--success">
                        <CheckCircle2 size={18} />
                        <div>
                          <strong>Clause Detected in Policy:</strong>
                          <span>
                            {' '}The document contains text satisfying the keyword and regex patterns for {activeIndicator.id}.
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="status-banner status-banner--warning">
                        <AlertTriangle size={18} />
                        <div>
                          <strong>Potential Compliance Gap:</strong>
                          <span>
                            {' '}No clauses satisfying the statutory criteria for {activeIndicator.id} were identified in the document text.
                          </span>
                        </div>
                      </div>
                    )
                  ) : (
                    <div className="status-banner status-banner--neutral">
                      <Info size={18} />
                      <div>
                        <strong>No Active Analysis:</strong>
                        <span> Upload a policy PDF to test this indicator against real text.</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Extracted Evidence Excerpts */}
              <div className="detail-section">
                <h4 className="detail-section-heading">
                  Extracted Evidence ({activeIndicator.evidence.length})
                </h4>
                {activeIndicator.evidence.length > 0 ? (
                  <div className="evidence-snippets-list">
                    {activeIndicator.evidence.map((snippet, idx) => {
                      const snippetText =
                        typeof snippet === 'string' ? snippet : snippet?.text || ''
                      return (
                        <div key={idx} className="evidence-snippet-box">
                          <div className="evidence-snippet-header">
                            <span className="evidence-snippet-num">Excerpt #{idx + 1}</span>
                            <span className="evidence-verified-tag">Verbatim Match</span>
                          </div>
                          <blockquote className="evidence-snippet-text">
                            "{snippetText}"
                          </blockquote>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="evidence-empty-box">
                    <p>No supporting evidence passages were detected in the analyzed text.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Detail Panel Actions Footer */}
            <div className="detail-panel-footer">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => {
                  if (onSelectIndicatorForEvidence) {
                    onSelectIndicatorForEvidence(activeIndicator.id)
                  }
                  onNavigate('evidence')
                }}
              >
                <Search size={15} />
                <span>Open in Evidence Explorer</span>
              </button>

              <button
                type="button"
                className="btn btn--primary"
                onClick={() => {
                  if (onSelectIndicatorForAgent) {
                    onSelectIndicatorForAgent(activeIndicator)
                  }
                  onNavigate('agents')
                }}
              >
                <Sparkles size={15} />
                <span>Verify with Multi-Agent Pool</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
