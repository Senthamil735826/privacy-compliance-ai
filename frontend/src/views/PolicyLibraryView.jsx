import React, { useState } from 'react'
import {
  BookOpen,
  Search,
  UploadCloud,
  FileText,
  CheckCircle2,
  Trash2,
  ArrowRight,
  Clock,
  HardDrive,
} from 'lucide-react'
import { StatusBadge } from '../components/StatusBadge'

export function PolicyLibraryView({
  library = [],
  activeDocumentId,
  onSelectPolicy,
  onDeletePolicy,
  onNavigate,
}) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredLibrary = library.filter((item) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      item.name?.toLowerCase().includes(q) ||
      item.id?.toLowerCase().includes(q)
    )
  })

  return (
    <div className="view-container">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div className="page-badge">Document Repository</div>
          <h1 className="page-title">Policy Library</h1>
          <p className="page-subtitle">
            Manage your analyzed policy documents, review historical compliance audits, and switch active workspaces.
          </p>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => onNavigate('analyze')}
          >
            <UploadCloud size={16} />
            <span>Upload New Policy</span>
          </button>
        </div>
      </div>

      {/* Search / Filter Bar */}
      <div className="table-controls-bar card">
        <div className="search-input-wrapper">
          <Search size={16} className="search-input-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search policies by document title or reference ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Library Table or Empty State */}
      {filteredLibrary.length === 0 ? (
        <div className="card overview-empty-state">
          <div className="overview-empty-icon" aria-hidden="true">
            <BookOpen size={36} />
          </div>
          <h3 className="overview-empty-title">
            {library.length === 0 ? 'No Policies in Library Yet' : 'No Policies Match Search'}
          </h3>
          <p className="overview-empty-desc">
            {library.length === 0
              ? 'When you analyze privacy policies, they are indexed here for quick access, indicator inspection, and multi-version comparison.'
              : 'Try searching with a different filename or keyword.'}
          </p>
          <div className="overview-empty-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => onNavigate('analyze')}
            >
              <UploadCloud size={16} />
              <span>Analyze Your First Policy</span>
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Mobile Card List (< 768px) */}
          <div className="policy-mobile-card-list">
            {filteredLibrary.map((item) => {
              const isActive = item.id === activeDocumentId
              return (
                <div
                  key={item.id}
                  className={`card policy-mobile-card ${isActive ? 'policy-mobile-card--active' : ''}`}
                >
                  <div className="policy-mobile-header">
                    <div className="policy-doc-title">
                      <FileText size={18} className="policy-doc-icon" />
                      <span>{item.name}</span>
                    </div>
                    {isActive && (
                      <span className="active-workspace-badge">Active</span>
                    )}
                  </div>

                  <div className="policy-mobile-meta">
                    <div className="policy-date-cell">
                      <Clock size={13} />
                      <span>{item.date || 'Recent'}</span>
                    </div>
                    <span className="coverage-badge-bold">
                      Coverage: {item.coverage || '—'}
                    </span>
                    <span className="policy-indicators-count">
                      {item.matched || 0}/{item.total || 40} detected
                    </span>
                  </div>

                  <div className="policy-mobile-actions">
                    {!isActive && (
                      <button
                        type="button"
                        className="btn btn--outline-sm"
                        onClick={() => onSelectPolicy(item)}
                      >
                        Set Active
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn--primary-sm"
                      onClick={() => {
                        onSelectPolicy(item)
                        onNavigate('overview')
                      }}
                    >
                      <span>Open Overview</span>
                      <ArrowRight size={13} />
                    </button>
                    {onDeletePolicy && (
                      <button
                        type="button"
                        className="btn-trash-row"
                        title="Delete from library"
                        onClick={() => onDeletePolicy(item.id)}
                        aria-label={`Delete ${item.name}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop Table (>= 768px) */}
          <div className="card table-card policy-desktop-table">
            <div className="table-responsive">
              <table className="symbolon-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '240px' }}>Policy Document</th>
                    <th style={{ width: '150px' }}>Audit Date</th>
                    <th style={{ width: '130px' }}>Status</th>
                    <th style={{ width: '150px' }}>Coverage</th>
                    <th style={{ width: '150px' }}>Indicators</th>
                    <th style={{ width: '180px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLibrary.map((item) => {
                    const isActive = item.id === activeDocumentId
                    return (
                      <tr
                        key={item.id}
                        className={`table-row-hover ${isActive ? 'table-row--active-workspace' : ''}`}
                      >
                        <td>
                          <div className="policy-doc-cell">
                            <FileText size={18} className="policy-doc-icon" />
                            <div>
                              <div className="policy-doc-title">
                                {item.name}
                                {isActive && (
                                  <span className="active-workspace-badge">Active</span>
                                )}
                              </div>
                              <span className="policy-doc-id">ID: {item.id}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="policy-date-cell">
                            <Clock size={13} />
                            <span>{item.date || 'Recent'}</span>
                          </div>
                        </td>
                        <td>
                          <StatusBadge status="compliant" label="Audit Ready" size="small" />
                        </td>
                        <td>
                          <span className="coverage-badge-bold">
                            {item.coverage || '—'}
                          </span>
                        </td>
                        <td>
                          <span className="policy-indicators-count">
                            <strong>{item.matched || 0}</strong> / {item.total || 40} detected
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div className="library-actions-group">
                            {!isActive && (
                              <button
                                type="button"
                                className="btn btn--outline-sm"
                                onClick={() => onSelectPolicy(item)}
                              >
                                Load
                              </button>
                            )}
                            <button
                              type="button"
                              className="btn btn--primary-sm"
                              onClick={() => {
                                onSelectPolicy(item)
                                onNavigate('overview')
                              }}
                            >
                              <span>Open</span>
                              <ArrowRight size={13} />
                            </button>
                            {onDeletePolicy && (
                              <button
                                type="button"
                                className="btn-trash-row"
                                title="Delete from library"
                                onClick={() => onDeletePolicy(item.id)}
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
