import React, { useMemo, useState } from 'react'
import {
  GitCompare,
  UploadCloud,
  ArrowRight,
  CheckCircle2,
  XCircle,
  HelpCircle,
  FileText,
  AlertCircle,
  ArrowRightLeft,
} from 'lucide-react'
import { StatusBadge } from '../components/StatusBadge'
import { SECONDARY_INDICATORS } from '../data/indicatorsData'

export function PolicyCompareView({
  library = [],
  onNavigate,
}) {
  const hasMultiple = library.length >= 2

  const [policyAId, setPolicyAId] = useState(library[0]?.id || '')
  const [policyBId, setPolicyBId] = useState(library[1]?.id || '')
  const [diffFilter, setDiffFilter] = useState('ALL') // ALL, DIFFERENCES_ONLY

  const policyA = useMemo(() => library.find((p) => p.id === policyAId), [library, policyAId])
  const policyB = useMemo(() => library.find((p) => p.id === policyBId), [library, policyBId])

  // Build comparison rows across all 40 indicators
  const comparisonRows = useMemo(() => {
    if (!policyA || !policyB) return []

    const mapA = new Map(policyA.analysis?.indicators?.map((i) => [i.id, i.matched]) || [])
    const mapB = new Map(policyB.analysis?.indicators?.map((i) => [i.id, i.matched]) || [])

    return SECONDARY_INDICATORS.map((sec) => {
      const matchA = Boolean(mapA.get(sec.id))
      const matchB = Boolean(mapB.get(sec.id))

      let deltaType = 'EQUAL' // EQUAL, ADDED_IN_B, REMOVED_IN_B, MISSING_BOTH
      if (matchA && matchB) {
        deltaType = 'BOTH_DETECTED'
      } else if (!matchA && matchB) {
        deltaType = 'ADDED_IN_B'
      } else if (matchA && !matchB) {
        deltaType = 'REMOVED_IN_B'
      } else {
        deltaType = 'MISSING_BOTH'
      }

      return {
        ...sec,
        matchA,
        matchB,
        deltaType,
        isDiff: matchA !== matchB,
      }
    })
  }, [policyA, policyB])

  const filteredRows = useMemo(() => {
    if (diffFilter === 'DIFFERENCES_ONLY') {
      return comparisonRows.filter((r) => r.isDiff)
    }
    return comparisonRows
  }, [comparisonRows, diffFilter])

  return (
    <div className="view-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div className="page-badge">Version Differential Analysis</div>
          <h1 className="page-title">Policy Comparison</h1>
          <p className="page-subtitle">
            Compare indicator coverage, statutory provision changes, and compliance gaps between policy revisions.
          </p>
        </div>
      </div>

      {!hasMultiple ? (
        /* Honest placeholder state when fewer than 2 policies analyzed */
        <div className="card overview-empty-state">
          <div className="overview-empty-icon" aria-hidden="true">
            <GitCompare size={36} />
          </div>
          <h3 className="overview-empty-title">Multi-Version Comparison Ready</h3>
          <p className="overview-empty-desc">
            Differential comparison requires at least two analyzed policies in your repository.
            Currently, you have <strong>{library.length}</strong> policy loaded.
          </p>
          <div className="compare-preview-box">
            <span className="compare-preview-label">How Comparison Works</span>
            <ul className="compare-features-list">
              <li>
                <CheckCircle2 size={16} className="text-success" />
                <span>Side-by-side indicator detection delta across 40 statutory requirements</span>
              </li>
              <li>
                <CheckCircle2 size={16} className="text-success" />
                <span>Identification of introduced protections vs. newly missing provisions</span>
              </li>
              <li>
                <CheckCircle2 size={16} className="text-success" />
                <span>Statutory coverage evolution tracking across product terms revisions</span>
              </li>
            </ul>
          </div>
          <div className="overview-empty-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => onNavigate('analyze')}
            >
              <UploadCloud size={16} />
              <span>Upload Second Policy for Comparison</span>
            </button>
          </div>
        </div>
      ) : (
        /* Side-by-side comparison workspace */
        <div className="compare-workspace">
          {/* Policy Selectors Card */}
          <div className="card compare-selectors-card">
            <div className="compare-selector-col">
              <label className="form-label">Base Policy (Version A)</label>
              <select
                className="form-select"
                value={policyAId}
                onChange={(e) => setPolicyAId(e.target.value)}
              >
                {library.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.coverage || 'Audit ready'})
                  </option>
                ))}
              </select>
              {policyA && (
                <div className="compare-doc-stats">
                  <span>Coverage: <strong>{policyA.coverage || '—'}</strong></span>
                  <span>•</span>
                  <span>Detected: <strong>{policyA.matched || 0}/40</strong></span>
                </div>
              )}
            </div>

            <div className="compare-switch-col">
              <button
                type="button"
                className="btn-compare-swap"
                title="Swap Base and Comparison"
                aria-label="Swap Base and Comparison"
                onClick={() => {
                  const temp = policyAId
                  setPolicyAId(policyBId)
                  setPolicyBId(temp)
                }}
              >
                <ArrowRightLeft size={16} />
              </button>
            </div>

            <div className="compare-selector-col">
              <label className="form-label">Comparison Policy (Version B)</label>
              <select
                className="form-select"
                value={policyBId}
                onChange={(e) => setPolicyBId(e.target.value)}
              >
                {library.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.coverage || 'Audit ready'})
                  </option>
                ))}
              </select>
              {policyB && (
                <div className="compare-doc-stats">
                  <span>Coverage: <strong>{policyB.coverage || '—'}</strong></span>
                  <span>•</span>
                  <span>Detected: <strong>{policyB.matched || 0}/40</strong></span>
                </div>
              )}
            </div>
          </div>

          {/* Differential Filter Bar */}
          <div className="table-controls-bar card">
            <div className="filter-button-group">
              <button
                type="button"
                className={`filter-btn ${diffFilter === 'ALL' ? 'filter-btn--active' : ''}`}
                onClick={() => setDiffFilter('ALL')}
              >
                All ({comparisonRows.length})
              </button>
              <button
                type="button"
                className={`filter-btn ${diffFilter === 'DIFFERENCES_ONLY' ? 'filter-btn--active' : ''}`}
                onClick={() => setDiffFilter('DIFFERENCES_ONLY')}
              >
                Differences Only ({comparisonRows.filter((r) => r.isDiff).length})
              </button>
            </div>
          </div>

          {/* Mobile Comparison Cards (< 768px) */}
          <div className="compare-mobile-card-list">
            {filteredRows.map((row) => (
              <div
                key={row.id}
                className={`card compare-mobile-card ${row.isDiff ? 'compare-mobile-card--diff' : ''}`}
              >
                <div className="compare-mobile-top">
                  <div className="mobile-card-id-group">
                    <span className="indicator-id-badge">{row.id}</span>
                    <span className="indicator-category-tag">{row.primary}</span>
                  </div>
                  <div>
                    {row.deltaType === 'BOTH_DETECTED' && (
                      <span className="diff-pill diff-pill--both">Identical</span>
                    )}
                    {row.deltaType === 'ADDED_IN_B' && (
                      <span className="diff-pill diff-pill--added">+ Added in B</span>
                    )}
                    {row.deltaType === 'REMOVED_IN_B' && (
                      <span className="diff-pill diff-pill--removed">- Missing in B</span>
                    )}
                    {row.deltaType === 'MISSING_BOTH' && (
                      <span className="diff-pill diff-pill--none">Missing in Both</span>
                    )}
                  </div>
                </div>

                <h4 className="compare-mobile-title">{row.name}</h4>

                <div className="compare-mobile-findings-row">
                  <div className="compare-finding-item">
                    <span className="compare-finding-label">Version A:</span>
                    <StatusBadge
                      status={row.matchA ? 'detected' : 'not_found'}
                      label={row.matchA ? 'Detected' : 'Missing'}
                      size="small"
                    />
                  </div>
                  <div className="compare-finding-item">
                    <span className="compare-finding-label">Version B:</span>
                    <StatusBadge
                      status={row.matchB ? 'detected' : 'not_found'}
                      label={row.matchB ? 'Detected' : 'Missing'}
                      size="small"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop Table (>= 768px) */}
          <div className="card table-card compare-desktop-table">
            <div className="table-responsive">
              <table className="symbolon-table">
                <thead>
                  <tr>
                    <th style={{ width: '85px' }}>ID</th>
                    <th>Indicator Name</th>
                    <th style={{ width: '130px' }}>Category</th>
                    <th style={{ width: '160px', textAlign: 'center' }}>Version A Finding</th>
                    <th style={{ width: '160px', textAlign: 'center' }}>Version B Finding</th>
                    <th style={{ width: '170px', textAlign: 'right' }}>Differential Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => {
                    return (
                      <tr key={row.id} className={row.isDiff ? 'table-row--diff-highlight' : ''}>
                        <td>
                          <span className="indicator-id-badge">{row.id}</span>
                        </td>
                        <td>
                          <div className="indicator-name-cell">
                            <span className="indicator-name-primary">{row.name}</span>
                          </div>
                        </td>
                        <td>
                          <span className="indicator-category-tag">{row.primary}</span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <StatusBadge
                            status={row.matchA ? 'detected' : 'not_found'}
                            label={row.matchA ? 'Detected' : 'Not Found'}
                            size="small"
                          />
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <StatusBadge
                            status={row.matchB ? 'detected' : 'not_found'}
                            label={row.matchB ? 'Detected' : 'Not Found'}
                            size="small"
                          />
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {row.deltaType === 'BOTH_DETECTED' && (
                            <span className="diff-pill diff-pill--both">Identical (Detected)</span>
                          )}
                          {row.deltaType === 'ADDED_IN_B' && (
                            <span className="diff-pill diff-pill--added">+ Added in Version B</span>
                          )}
                          {row.deltaType === 'REMOVED_IN_B' && (
                            <span className="diff-pill diff-pill--removed">- Missing in Version B</span>
                          )}
                          {row.deltaType === 'MISSING_BOTH' && (
                            <span className="diff-pill diff-pill--none">Missing in Both</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
