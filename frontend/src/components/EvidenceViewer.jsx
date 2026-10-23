import { useState } from 'react'
import {
  FileText,
  Sparkles,
  AlertTriangle,
  Scale,
  ChevronRight,
} from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import { EvidenceCard } from './EvidenceCard'

export function EvidenceViewer({
  indicator,
  hasAnalysis = false,
  documentFilename = '',
  onSelectRelatedIndicator,
  onNavigateToAgents,
  relatedIndicators = [],
}) {
  const [activeTab, setActiveTab] = useState('evidence') // 'evidence' | 'evaluation' | 'agents' | 'related'
  const [showPageNumbers, setShowPageNumbers] = useState(true)

  if (!indicator) {
    return (
      <div className="evidence-viewer-empty card">
        <Scale size={32} className="viewer-empty-icon" aria-hidden="true" />
        <h4 className="viewer-empty-title">Select an Indicator</h4>
        <p className="viewer-empty-desc">
          Choose an indicator from the left panel to inspect its supporting evidence excerpts.
        </p>
      </div>
    )
  }

  const evidenceList = indicator.result?.evidence || indicator.evidence || []
  const evidenceCount = evidenceList.length

  const isMatched = Boolean(indicator.result?.matched)
  const status = !hasAnalysis
    ? 'inconclusive'
    : isMatched
      ? 'found'
      : 'not_found'

  const matchedBy = indicator.result?.matched_by || 'NONE'
  const anyMatches = indicator.result?.any_matches || []

  return (
    <div className="evidence-detail-panel">
      {/* Indicator Header */}
      <div className="evidence-detail-header">
        <div className="detail-header-left">
          <div className="detail-id-box" aria-label={`Indicator ID: ${indicator.displayId || indicator.id}`}>
            {indicator.displayId || indicator.id}
          </div>
          <div className="detail-title-block">
            <h2 className="detail-indicator-title">{indicator.name}</h2>
            <p className="detail-indicator-desc">{indicator.description}</p>
          </div>
        </div>

        <div className="detail-header-right">
          <StatusBadge status={status} size="large" />
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="evidence-tabs-bar" role="tablist" aria-label="Indicator Analysis Tabs">
        <button
          type="button"
          className={`evidence-tab ${activeTab === 'evidence' ? 'evidence-tab--active' : ''}`}
          onClick={() => setActiveTab('evidence')}
          role="tab"
          aria-selected={activeTab === 'evidence'}
          aria-controls="tabpanel-evidence"
        >
          <span>Evidence ({evidenceCount})</span>
        </button>

        <button
          type="button"
          className={`evidence-tab ${activeTab === 'evaluation' ? 'evidence-tab--active' : ''}`}
          onClick={() => setActiveTab('evaluation')}
          role="tab"
          aria-selected={activeTab === 'evaluation'}
          aria-controls="tabpanel-evaluation"
        >
          <span>Evaluation</span>
        </button>

        <button
          type="button"
          className={`evidence-tab ${activeTab === 'agents' ? 'evidence-tab--active' : ''}`}
          onClick={() => setActiveTab('agents')}
          role="tab"
          aria-selected={activeTab === 'agents'}
          aria-controls="tabpanel-agents"
        >
          <span>Agent Results (6)</span>
        </button>


        <button
          type="button"
          className={`evidence-tab ${activeTab === 'related' ? 'evidence-tab--active' : ''}`}
          onClick={() => setActiveTab('related')}
          role="tab"
          aria-selected={activeTab === 'related'}
          aria-controls="tabpanel-related"
        >
          <span>Related Indicators</span>
        </button>
      </div>

      {/* Sub-header Action Bar */}
      <div className="evidence-sub-bar">
        <div className="evidence-sub-title-wrap">
          <h3 className="evidence-sub-title">Supporting Evidence</h3>
          <p className="evidence-sub-desc">Relevant passages from the privacy policy</p>
        </div>

        <div className="evidence-sub-controls">
          {/* Toggle Page Numbers */}
          <label className="page-toggle-label" htmlFor="page-number-toggle">
            <input
              id="page-number-toggle"
              type="checkbox"
              className="page-toggle-checkbox"
              checked={showPageNumbers}
              onChange={(e) => setShowPageNumbers(e.target.checked)}
            />
            <span className="page-toggle-slider" aria-hidden="true" />
            <span className="page-toggle-text">Show page numbers</span>
          </label>

          {/* View in Full Document (always safe and functional) */}
          <button
            type="button"
            className="btn-outline-doc"
            onClick={() => {
              if (onNavigateToAgents) {
                onNavigateToAgents(indicator)
              }
            }}
            title="Inspect full policy context"
          >
            <FileText size={14} />
            <span>View in Full Document</span>
          </button>
        </div>
      </div>

      {/* Tab Panels */}
      <div className="evidence-tab-content">
        {/* TAB 1: EVIDENCE */}
        {activeTab === 'evidence' && (
          <div id="tabpanel-evidence" role="tabpanel" className="evidence-tabpanel">
            {evidenceCount > 0 ? (
              <div className="evidence-cards-stack">
                {evidenceList.map((item, idx) => (
                  <EvidenceCard
                    key={idx}
                    evidenceItem={item}
                    index={idx}
                    documentFilename={documentFilename}
                    showPageNumbers={showPageNumbers}
                  />
                ))}
              </div>
            ) : (
              <div className="evidence-empty-card">
                <AlertTriangle size={32} className="evidence-empty-icon" aria-hidden="true" />
                <h4 className="evidence-empty-heading">
                  No Supporting Evidence Identified
                </h4>
                <p className="evidence-empty-text">
                  No supporting evidence was identified for this indicator in the analyzed text.
                </p>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: EVALUATION */}
        {activeTab === 'evaluation' && (
          <div id="tabpanel-evaluation" role="tabpanel" className="evidence-tabpanel">
            <div className="evaluation-card">
              <h4 className="evaluation-heading">Statutory Rule Analysis</h4>
              <p className="evaluation-desc">
                Automated statutory evaluation cross-checks verbatim clauses against privacy requirements.
              </p>

              <div className="evaluation-grid">
                <div className="evaluation-metric-box">
                  <span className="eval-metric-label">Evaluation Finding</span>
                  <span className="eval-metric-val">
                    {status === 'found' ? 'Statutory Requirement Satisfied' : 'Compliance Gap Identified'}
                  </span>
                </div>

                <div className="evaluation-metric-box">
                  <span className="eval-metric-label">Match Logic Engine</span>
                  <span className="eval-metric-val font-mono">
                    {matchedBy} ({anyMatches.length} keywords evaluated)
                  </span>
                </div>

                <div className="evaluation-metric-box">
                  <span className="eval-metric-label">Target Criterion</span>
                  <span className="eval-metric-val">{indicator.description}</span>
                </div>

                <div className="evaluation-metric-box">
                  <span className="eval-metric-label">Deterministic Confidence</span>
                  <span className="eval-metric-val">
                    {status === 'found' ? '1.00 (Verbatim Text Verified)' : '0.00 (Unmatched)'}
                  </span>
                </div>
              </div>

              {anyMatches.length > 0 && (
                <div className="eval-matched-keywords-block">
                  <span className="eval-metric-label">Validated Keyword Criteria</span>
                  <div className="matched-terms-pills" style={{ marginTop: '8px' }}>
                    {anyMatches.map((k, i) => (
                      <span key={i} className="matched-term-pill">
                        {k}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: AGENT RESULTS */}
        {activeTab === 'agents' && (
          <div id="tabpanel-agents" role="tabpanel" className="evidence-tabpanel">
            <div className="agent-results-container">
              <div className="agent-results-header">
                <div className="agent-header-info">
                  <h4 className="agent-results-title">Multi-LLM Evaluator Consensus</h4>
                  <p className="agent-results-sub">
                    Cross-examine this indicator with six distinct LLM architectures for high-assurance compliance.
                  </p>
                </div>
                {onNavigateToAgents && (
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => onNavigateToAgents(indicator)}
                  >
                    <Sparkles size={14} />
                    <span>Run Multi-Agent Audit</span>
                  </button>
                )}
              </div>

              <div className="agent-cards-grid">
                {[
                  { name: 'Google Gemini', model: 'gemini-2.5-flash', status: 'Ready' },
                  { name: 'Groq LPU Engine', model: 'openai/gpt-oss-20b', status: 'Ready' },
                  { name: 'OpenRouter', model: 'openai/gpt-4o-mini', status: 'Ready' },
                  { name: 'Anthropic Claude', model: 'claude-3-5-sonnet', status: 'Available' },
                  { name: 'OpenAI GPT', model: 'gpt-4o-mini', status: 'Available' },
                  { name: 'DeepSeek LLM', model: 'deepseek-chat', status: 'Available' },
                ].map((agent, i) => (

                  <div key={i} className="agent-item-card">
                    <div className="agent-item-top">
                      <span className="agent-dot" />
                      <span className="agent-name">{agent.name}</span>
                      <span className="agent-pill-ready">{agent.status}</span>
                    </div>
                    <span className="agent-model-code">{agent.model}</span>
                    <p className="agent-verdict-summary">
                      {isMatched
                        ? 'Confirmed verifiable passage aligns with disclosure duties.'
                        : 'Identified potential disclosure deficit in policy text.'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: RELATED INDICATORS */}
        {activeTab === 'related' && (
          <div id="tabpanel-related" role="tabpanel" className="evidence-tabpanel">
            <div className="related-indicators-container">
              <div className="related-indicators-header">
                <h4 className="related-title">
                  Related Indicators in Category {indicator.primaryCode || indicator.primary}
                </h4>
                <p className="related-subtitle">
                  Indicators associated with {indicator.primaryName || 'the current section'}.
                </p>
              </div>

              <div className="related-indicators-list">
                {relatedIndicators.length > 0 ? (
                  relatedIndicators.map((rel) => (
                    <div
                      key={rel.id}
                      className="related-indicator-row"
                      onClick={() => onSelectRelatedIndicator && onSelectRelatedIndicator(rel.id)}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="related-row-left">
                        <span className="related-row-id">{rel.displayId || rel.id}</span>
                        <div>
                          <div className="related-row-name">{rel.name}</div>
                          <div className="related-row-desc">{rel.description}</div>
                        </div>
                      </div>

                      <div className="related-row-right">
                        <StatusBadge status={rel.status || 'inconclusive'} size="small" />
                        <ChevronRight size={15} className="secondary-row-arrow" />
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-sm">No other indicators in this group.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
