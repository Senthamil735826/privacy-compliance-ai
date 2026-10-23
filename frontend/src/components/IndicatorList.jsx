import { useState, useMemo, useEffect, useRef } from 'react'
import { Search, ChevronDown, ChevronRight, MoreVertical, RotateCcw } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

// Canonical mapping of the 7 primary groups
const PRIMARY_GROUP_META = {
  A1: { code: 'A1', name: 'Data Collection' },
  A2: { code: 'A2', name: 'Purpose Specification' },
  A3: { code: 'A3', name: 'Legal Basis' },
  A4: { code: 'A4', name: 'Data Retention' },
  A5: { code: 'A5', name: 'Subject Rights' },
  A6: { code: 'A6', name: 'Third-Party Sharing' },
  A7: { code: 'A7', name: "Children's Privacy" },
}

export function IndicatorList({
  primaryCategories = [],
  secondaryIndicators = [],
  analysisMap = new Map(),
  hasAnalysis = false,
  selectedIndicatorId,
  onSelectIndicator,
}) {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL') // ALL, FOUND, NOT_FOUND, INCONCLUSIVE
  const [expandedGroups, setExpandedGroups] = useState({
    A1: true,
    A2: true,
    A3: true,
    A4: true,
    A5: true,
    A6: true,
    A7: true,
  })

  const listContainerRef = useRef(null)

  // Enrich indicators with evaluation result and display aliases
  const enrichedIndicators = useMemo(() => {
    return secondaryIndicators.map((sec) => {
      const res = analysisMap.get(sec.id)
      const primaryMeta = PRIMARY_GROUP_META[sec.primary] || {
        code: sec.primary,
        name: sec.primary,
      }

      const displayId = sec.id

      let status = 'inconclusive'
      if (!hasAnalysis) {
        status = 'inconclusive'
      } else if (res?.matched === true) {
        status = 'found'
      } else if (res?.matched === false) {
        status = 'not_found'
      }

      return {
        ...sec,
        displayId,
        primaryCode: primaryMeta.code,
        primaryName: primaryMeta.name,
        status,
        result: res,
        evidenceCount: res?.evidence?.length || 0,
      }
    })
  }, [secondaryIndicators, analysisMap, hasAnalysis])

  // Compute live counts
  const counts = useMemo(() => {
    let found = 0
    let notFound = 0
    let inconclusive = 0

    enrichedIndicators.forEach((item) => {
      if (item.status === 'found') found++
      else if (item.status === 'not_found') notFound++
      else inconclusive++
    })

    return {
      total: enrichedIndicators.length,
      found,
      notFound,
      inconclusive,
    }
  }, [enrichedIndicators])

  // Filter indicators based on search and status
  const filteredIndicators = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()

    return enrichedIndicators.filter((item) => {
      // Status filter
      if (statusFilter === 'FOUND' && item.status !== 'found') return false
      if (statusFilter === 'NOT_FOUND' && item.status !== 'not_found') return false
      if (statusFilter === 'INCONCLUSIVE' && item.status !== 'inconclusive') return false

      // Search filter
      if (query) {
        const inId = item.id.toLowerCase().includes(query)
        const inDisplayId = item.displayId.toLowerCase().includes(query)
        const inName = item.name.toLowerCase().includes(query)
        const inDesc = (item.description || '').toLowerCase().includes(query)
        const inPrimary = item.primaryName.toLowerCase().includes(query)

        if (!inId && !inDisplayId && !inName && !inDesc && !inPrimary) {
          return false
        }
      }

      return true
    })
  }, [enrichedIndicators, statusFilter, searchTerm])

  // Auto-expand groups when searching
  useEffect(() => {
    if (searchTerm.trim()) {
      const newExpanded = {}
      primaryCategories.forEach((p) => {
        newExpanded[p.id] = true
      })
      setExpandedGroups(newExpanded)
    }
  }, [searchTerm, primaryCategories])

  function toggleGroup(groupId) {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }))
  }

  function handleResetFilters() {
    setSearchTerm('')
    setStatusFilter('ALL')
  }

  // Keyboard navigation across indicators
  function handleKeyDown(e, indicator) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelectIndicator(indicator.id)
    }
  }

  return (
    <div className="indicators-panel" ref={listContainerRef}>
      {/* Panel Header */}
      <div className="indicators-panel-header">
        <div className="indicators-header-top">
          <div className="indicators-title-wrap">
            <h3 className="indicators-panel-title">Indicators</h3>
            <span className="indicators-panel-subtitle">
              7 primary · {counts.total} secondary indicators
            </span>
          </div>

          <button
            type="button"
            className="indicators-kebab-btn"
            aria-label="Indicator options"
            title="More options"
          >
            <MoreVertical size={16} />
          </button>
        </div>

        {/* Search input */}
        <div className="indicators-search-box">
          <Search size={15} className="indicators-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="indicators-search-input"
            placeholder="Search indicators..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            aria-label="Search indicators by ID, name or description"
          />
        </div>

        {/* Filter chips with live counts */}
        <div className="indicators-filter-chips" role="tablist" aria-label="Status Filters">
          <button
            type="button"
            className={`indicator-chip ${statusFilter === 'ALL' ? 'indicator-chip--active' : ''}`}
            onClick={() => setStatusFilter('ALL')}
            role="tab"
            aria-selected={statusFilter === 'ALL'}
          >
            <span>All</span>
            <span className="indicator-chip-count">{counts.total}</span>
          </button>

          <button
            type="button"
            className={`indicator-chip indicator-chip--found ${statusFilter === 'FOUND' ? 'indicator-chip--active' : ''}`}
            onClick={() => setStatusFilter('FOUND')}
            role="tab"
            aria-selected={statusFilter === 'FOUND'}
          >
            <span>Found</span>
            <span className="indicator-chip-count">{counts.found}</span>
          </button>

          <button
            type="button"
            className={`indicator-chip indicator-chip--not-found ${statusFilter === 'NOT_FOUND' ? 'indicator-chip--active' : ''}`}
            onClick={() => setStatusFilter('NOT_FOUND')}
            role="tab"
            aria-selected={statusFilter === 'NOT_FOUND'}
          >
            <span>Not Found</span>
            <span className="indicator-chip-count">{counts.notFound}</span>
          </button>

          <button
            type="button"
            className={`indicator-chip indicator-chip--inconclusive ${statusFilter === 'INCONCLUSIVE' ? 'indicator-chip--active' : ''}`}
            onClick={() => setStatusFilter('INCONCLUSIVE')}
            role="tab"
            aria-selected={statusFilter === 'INCONCLUSIVE'}
          >
            <span>Inconclusive</span>
            <span className="indicator-chip-count">{counts.inconclusive}</span>
          </button>
        </div>
      </div>

      {/* Accordion List Body */}
      <div className="indicators-accordion-body">
        {filteredIndicators.length === 0 ? (
          <div className="indicators-empty-search">
            <p className="indicators-empty-title">No indicators match your search.</p>
            <button
              type="button"
              className="indicators-reset-btn"
              onClick={handleResetFilters}
            >
              <RotateCcw size={14} />
              <span>Reset filters</span>
            </button>
          </div>
        ) : (
          primaryCategories.map((cat) => {
            const groupMeta = PRIMARY_GROUP_META[cat.id] || { code: cat.id, name: cat.name }
            const children = filteredIndicators.filter((item) => item.primary === cat.id)

            // If filter or search hides all children of this group, omit group
            if (children.length === 0) return null

            const isExpanded = Boolean(expandedGroups[cat.id])
            const totalSecCount = (cat.secondaryIds || []).length

            // Compute group aggregate status
            const foundCount = children.filter((c) => c.status === 'found').length
            const groupStatus =
              foundCount === children.length && children.length > 0
                ? 'found'
                : foundCount > 0
                  ? 'inconclusive'
                  : 'not_found'

            return (
              <div key={cat.id} className="indicator-group-block">
                {/* Primary Group Header Row */}
                <button
                  type="button"
                  className={`indicator-group-row ${isExpanded ? 'indicator-group-row--expanded' : ''}`}
                  onClick={() => toggleGroup(cat.id)}
                  aria-expanded={isExpanded}
                  aria-controls={`group-content-${cat.id}`}
                >
                  <div className="indicator-group-left">
                    <span className="indicator-group-tag">{groupMeta.code}</span>
                    <div className="indicator-group-info">
                      <span className="indicator-group-name">{groupMeta.name}</span>
                      <span className="indicator-group-meta">
                        {totalSecCount} secondary indicators
                      </span>
                    </div>
                  </div>

                  <div className="indicator-group-right">
                    <StatusBadge
                      status={groupStatus}
                      label={groupStatus === 'found' ? 'Found' : groupStatus === 'inconclusive' ? 'Inconclusive' : 'Not Found'}
                      size="small"
                    />
                    <ChevronDown
                      size={15}
                      className={`group-chevron ${isExpanded ? 'group-chevron--rotated' : ''}`}
                      aria-hidden="true"
                    />
                  </div>
                </button>

                {/* Secondary Indicators List */}
                {isExpanded && (
                  <div
                    id={`group-content-${cat.id}`}
                    className="indicator-secondary-list"
                    role="list"
                  >
                    {children.map((ind) => {
                      const isSelected = ind.id === selectedIndicatorId
                      return (
                        <div
                          key={ind.id}
                          role="button"
                          tabIndex={0}
                          aria-selected={isSelected}
                          className={`indicator-secondary-row ${isSelected ? 'indicator-secondary-row--selected' : ''}`}
                          onClick={() => onSelectIndicator(ind.id)}
                          onKeyDown={(e) => handleKeyDown(e, ind)}
                        >
                          <div className="indicator-secondary-left">
                            <span className="indicator-secondary-id">
                              {ind.displayId || ind.id}
                            </span>
                            <span className="indicator-secondary-name" title={ind.name}>
                              {ind.name}
                            </span>
                          </div>

                          <div className="indicator-secondary-right">
                            <StatusBadge status={ind.status} size="small" />
                            <ChevronRight size={14} className="secondary-row-arrow" aria-hidden="true" />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
