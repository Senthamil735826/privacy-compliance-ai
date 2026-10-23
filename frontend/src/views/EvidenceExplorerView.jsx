import { useMemo, useState } from 'react'
import {
  FileText,
  AlertTriangle,
  RotateCcw,
  ChevronLeft,
} from 'lucide-react'
import { PRIMARY_CATEGORIES, SECONDARY_INDICATORS } from '../data/indicatorsData'
import { PolicySelector } from '../components/PolicySelector'
import { IndicatorList } from '../components/IndicatorList'
import { EvidenceViewer } from '../components/EvidenceViewer'

export function EvidenceExplorerView({
  analysis,
  activePolicyName = '',
  policies = [],
  onSelectPolicy,
  selectedIndicatorId = 'B7',
  onNavigate,
  onSelectIndicatorForAgent,
}) {
  const [selectedId, setSelectedId] = useState(null)
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState(null)

  const activeId = selectedId || selectedIndicatorId || 'B7'

  const hasAnalysis = Boolean(analysis && Array.isArray(analysis.indicators) && analysis.indicators.length > 0)

  // Map analysis results by ID
  const analysisMap = useMemo(() => {
    const map = new Map()
    if (analysis?.indicators) {
      for (const ind of analysis.indicators) {
        map.set(ind.id, ind)
      }
    }
    return map
  }, [analysis])

  // Get active indicator object
  const currentIndicator = useMemo(() => {
    const found = SECONDARY_INDICATORS.find((item) => item.id === activeId)
    if (!found) return null

    const res = analysisMap.get(found.id)
    const primaryCat = PRIMARY_CATEGORIES.find((p) => p.id === found.primary)

    return {
      ...found,
      displayId: found.id,
      primaryCode: found.primary,
      primaryName: primaryCat?.name || found.primary,
      result: res,
      evidence: res?.evidence || [],
    }
  }, [activeId, analysisMap])

  // Related indicators in same primary category
  const relatedIndicators = useMemo(() => {
    if (!currentIndicator) return []
    return SECONDARY_INDICATORS.filter(
      (item) => item.primary === currentIndicator.primary && item.id !== currentIndicator.id
    ).map((sec) => {
      const res = analysisMap.get(sec.id)

      return {
        ...sec,
        displayId: sec.id,
        status: !hasAnalysis ? 'inconclusive' : res?.matched ? 'found' : 'not_found',
      }
    })
  }, [currentIndicator, analysisMap, hasAnalysis])

  function handleSelectIndicator(id) {
    setSelectedId(id)
    setMobileDetailOpen(true)
  }

  function handleRetry() {
    setIsLoading(true)
    setLoadError(null)
    setTimeout(() => {
      setIsLoading(false)
    }, 600)
  }

  // Active policy filename for display
  const currentPolicyFilename =
    activePolicyName ||
    analysis?.document?.filename ||
    (policies && policies[0]?.name) ||
    ''

  return (
    <div className="evidence-explorer-page">
      {/* Page Header */}
      <header className="explorer-header">
        {/* Subtle decorative faded scales illustration (low opacity, background only) */}
        <div className="explorer-header-decor" aria-hidden="true">
          <svg viewBox="0 0 400 160" fill="none" className="header-decor-svg">
            <path
              d="M120 140H280M200 30V140M150 50L200 40L250 50M150 50L130 90M150 50L170 90M250 50L230 90M250 50L270 90M125 90C125 105 175 105 175 90H125ZM225 90C225 105 275 105 275 90H225Z"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M310 110L350 90V140L310 160V110ZM350 90L390 110V160L350 140V90ZM310 110L350 130L390 110"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.6"
            />
          </svg>
        </div>

        <div className="explorer-header-content">
          <div className="explorer-breadcrumb">
            <button
              type="button"
              className="breadcrumb-back-btn"
              onClick={() => onNavigate && onNavigate('overview')}
            >
              <span>‹</span>
              <span>Evidence Explorer</span>
            </button>
          </div>

          <div className="explorer-header-row">
            <div className="explorer-title-area">
              <h1 className="explorer-page-title">Evidence Explorer</h1>
              <p className="explorer-page-subtitle">
                Explore supporting evidence for each privacy indicator in the analyzed policy.
              </p>
            </div>

            {/* Policy Selector Card */}
            <div className="explorer-policy-selector-wrap">
              <PolicySelector
                activePolicyName={currentPolicyFilename}
                policies={policies}
                onSelectPolicy={onSelectPolicy}
                isAnalyzed={hasAnalysis}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      {isLoading ? (
        <div className="explorer-state-card explorer-loading-state">
          <div className="explorer-skeleton-columns">
            <div className="skeleton-box skeleton-box--panel" />
            <div className="skeleton-box skeleton-box--detail" />
          </div>
          <p className="explorer-state-text">Loading evidence...</p>
        </div>
      ) : loadError ? (
        <div className="explorer-state-card explorer-error-state card">
          <AlertTriangle size={36} className="state-error-icon" />
          <h3 className="explorer-state-title">Unable to load evidence. Please try again.</h3>
          <button type="button" className="btn btn--primary" onClick={handleRetry}>
            <RotateCcw size={15} />
            <span>Retry</span>
          </button>
        </div>
      ) : !currentPolicyFilename && !hasAnalysis ? (
        <div className="explorer-state-card explorer-no-policy-state card">
          <FileText size={42} className="state-empty-icon" />
          <h3 className="explorer-state-title">Select an analyzed privacy policy to explore its evidence.</h3>
          <p className="explorer-state-desc">
            Upload a policy in the Analyze Policy workspace or select an existing policy from your library.
          </p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => onNavigate && onNavigate('analyze')}
          >
            Go to Analyze Policy
          </button>
        </div>
      ) : (
        <div className="explorer-workspace-columns">
          {/* Left Column: Indicators Accordion Panel */}
          <div className={`explorer-col-left ${mobileDetailOpen ? 'explorer-col-left--mobile-hidden' : ''}`}>
            <IndicatorList
              primaryCategories={PRIMARY_CATEGORIES}
              secondaryIndicators={SECONDARY_INDICATORS}
              analysisMap={analysisMap}
              hasAnalysis={hasAnalysis}
              selectedIndicatorId={activeId}
              onSelectIndicator={handleSelectIndicator}
            />
          </div>

          {/* Right Column: Evidence Detail Panel */}
          <div className={`explorer-col-right ${mobileDetailOpen ? 'explorer-col-right--mobile-visible' : ''}`}>
            {/* Mobile Back Button */}
            {mobileDetailOpen && (
              <button
                type="button"
                className="mobile-back-to-indicators"
                onClick={() => setMobileDetailOpen(false)}
              >
                <ChevronLeft size={16} />
                <span>‹ Back to Indicators</span>
              </button>
            )}

            <EvidenceViewer
              indicator={currentIndicator}
              hasAnalysis={hasAnalysis}
              documentFilename={currentPolicyFilename}
              onSelectRelatedIndicator={(id) => {
                setSelectedId(id)
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
              onNavigateToAgents={(ind) => {
                if (onSelectIndicatorForAgent) {
                  onSelectIndicatorForAgent(ind)
                }
                if (onNavigate) {
                  onNavigate('agents')
                }
              }}
              relatedIndicators={relatedIndicators}
            />
          </div>
        </div>
      )}
    </div>
  )
}
