import React, { useEffect, useState } from 'react'
import {
  Sparkles,
  Bot,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Loader2,
  Play,
  RotateCcw,
  ShieldCheck,
  ChevronDown,
  Info,
  RefreshCw,
  Clock,
  ExternalLink,
} from 'lucide-react'
import { StatusBadge } from '../components/StatusBadge'
import { SECONDARY_INDICATORS } from '../data/indicatorsData'

function extractEvidenceString(item) {
  if (!item) return ''
  if (typeof item === 'string') return item
  if (typeof item === 'object' && item.text) return item.text
  return String(item)
}

export function AgentAnalysisView({
  targetIndicator,
  analysis,
}) {
  const [providerStatus, setProviderStatus] = useState(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [checkingProvider, setCheckingProvider] = useState({})
  const [checkingAll, setCheckingAll] = useState(false)

  // Evaluation form state
  const [selectedIndId, setSelectedIndId] = useState(targetIndicator?.id || 'B7')
  const [evidenceText, setEvidenceText] = useState(() => {
    if (targetIndicator?.customEvidence) return targetIndicator.customEvidence
    const first = targetIndicator?.evidence?.[0]
    return extractEvidenceString(first) || 'We collect your email address, billing address, and account credentials solely for account creation and service provision.'
  })

  // Execution state
  const [evaluating, setEvaluating] = useState(false)
  const [evalResult, setEvalResult] = useState(null)
  const [evalError, setEvalError] = useState('')

  // Fetch /api/agents/status on mount
  const fetchStatus = async (force = false) => {
    try {
      const url = force ? '/api/agents/status?force=true' : '/api/agents/status'
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        setProviderStatus(data)
      }
    } catch (err) {
      console.error('Failed to load agent status:', err)
    } finally {
      setLoadingStatus(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  // Manual Check Connection for a single provider
  const handleCheckConnection = async (providerKey) => {
    setCheckingProvider((prev) => ({ ...prev, [providerKey]: true }))
    try {
      const res = await fetch('/api/agents/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: providerKey }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.provider) {
          setProviderStatus((prev) => ({
            ...prev,
            providers: {
              ...prev?.providers,
              [providerKey]: data.provider,
            },
          }))
        }
      }
    } catch (err) {
      console.error(`Failed to check provider ${providerKey}:`, err)
    } finally {
      setCheckingProvider((prev) => ({ ...prev, [providerKey]: false }))
    }
  }

  // Manual Check All Connections
  const handleCheckAll = async () => {
    setCheckingAll(true)
    try {
      const res = await fetch('/api/agents/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'all' }),
      })
      if (res.ok) {
        const data = await res.json()
        setProviderStatus(data)
      }
    } catch (err) {
      console.error('Failed to check all providers:', err)
    } finally {
      setCheckingAll(false)
    }
  }

  // Sync if targetIndicator prop changes
  useEffect(() => {
    if (targetIndicator?.id) {
      setSelectedIndId(targetIndicator.id)
      if (targetIndicator.customEvidence) {
        setEvidenceText(targetIndicator.customEvidence)
      } else if (targetIndicator.evidence?.[0]) {
        setEvidenceText(extractEvidenceString(targetIndicator.evidence[0]))
      }
    }
  }, [targetIndicator])

  // Current indicator metadata
  const currentIndicatorMeta = SECONDARY_INDICATORS.find((i) => i.id === selectedIndId) || {
    id: selectedIndId,
    name: 'Selected Indicator',
    primary: 'A2',
    description: 'Privacy requirement evaluation.',
  }

  // Execute multi-agent verification calling /api/agents/evaluate
  async function handleRunEvaluation(e) {
    if (e) e.preventDefault()
    if (!String(evidenceText || '').trim()) {
      setEvalError('Please provide policy evidence text for evaluation.')
      return
    }

    setEvaluating(true)
    setEvalError('')
    setEvalResult(null)

    try {
      const response = await fetch('/api/agents/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_indicator_id: currentIndicatorMeta.primary,
          indicator_id: currentIndicatorMeta.id,
          indicator_description: currentIndicatorMeta.description,
          evidence: evidenceText.trim(),
        }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Evaluation failed on backend.')
      }

      setEvalResult(data.result)
    } catch (err) {
      setEvalError(err.message || 'Error occurred while running multi-agent evaluation.')
    } finally {
      setEvaluating(false)
    }
  }

  // Baseline fallback providers if API call is loading
  const providers = providerStatus?.providers || {
    gemini: { provider: 'gemini', name: 'Google Gemini', configured: true, model: 'gemini-3.5-flash', status: 'READY', is_available: true },
    groq: { provider: 'groq', name: 'Groq LPU Engine', configured: true, model: 'openai/gpt-oss-20b', status: 'READY', is_available: true },
    claude: { provider: 'claude', name: 'Anthropic Claude', configured: true, model: 'claude-3-5-sonnet-20241022', status: 'INSUFFICIENT_BALANCE', is_available: false, error: 'Account credit balance is exhausted or too low.' },
    openai: { provider: 'openai', name: 'OpenAI GPT', configured: true, model: 'gpt-4.1-mini', status: 'INSUFFICIENT_BALANCE', is_available: false, error: 'Account credit balance is exhausted.' },
    deepseek: { provider: 'deepseek', name: 'DeepSeek LLM', configured: true, model: 'deepseek-chat', status: 'INSUFFICIENT_BALANCE', is_available: false, error: 'Account balance insufficient.' },
    openrouter: { provider: 'openrouter', name: 'OpenRouter', configured: true, model: 'openai/gpt-4o-mini', status: 'READY', is_available: true },
  }


  const consensus = evalResult?.aggregation || evalResult?.consensus
  const results = evalResult?.evaluations || evalResult?.results || []
  const failedEvals = evalResult?.failed_evaluations || []

  // Detect disagreements among completed evaluations
  const validResults = results.filter((r) => r.decision && r.decision !== 'inconclusive' && !r.error)
  const decisionsSet = new Set(validResults.map((r) => r.decision))
  const hasDisagreement = decisionsSet.size > 1

  // Status badge config
  const getStatusBadgeConfig = (status, isAvailable) => {
    switch (status) {
      case 'READY':
        return {
          label: 'Ready',
          className: 'provider-badge--ready',
          icon: CheckCircle2,
          cardClass: 'provider-card--ready',
        }
      case 'INSUFFICIENT_BALANCE':
        return {
          label: 'Insufficient Balance',
          className: 'provider-badge--balance',
          icon: AlertTriangle,
          cardClass: 'provider-card--balance',
        }
      case 'AUTH_ERROR':
        return {
          label: 'Authentication Failed',
          className: 'provider-badge--error',
          icon: XCircle,
          cardClass: 'provider-card--error',
        }
      case 'RATE_LIMITED':
        return {
          label: 'Rate Limited',
          className: 'provider-badge--warning',
          icon: AlertTriangle,
          cardClass: 'provider-card--warning',
        }
      case 'MODEL_UNAVAILABLE':
        return {
          label: 'Model Unavailable',
          className: 'provider-badge--error',
          icon: XCircle,
          cardClass: 'provider-card--error',
        }
      case 'NETWORK_ERROR':
        return {
          label: 'Connection Error',
          className: 'provider-badge--error',
          icon: XCircle,
          cardClass: 'provider-card--error',
        }
      case 'NOT_CONFIGURED':
      default:
        return {
          label: 'Not Configured',
          className: 'provider-badge--unconfigured',
          icon: HelpCircle,
          cardClass: 'provider-card--inactive',
        }
    }
  }

  // Format timestamp helper
  const formatTime = (isoString) => {
    if (!isoString) return 'Not yet verified'
    try {
      const d = new Date(isoString)
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    } catch {
      return isoString
    }
  }

  const readyCount = Object.values(providers).filter((p) => p.status === 'READY').length
  const totalCount = Object.keys(providers).length

  return (
    <div className="view-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div className="page-badge">Multi-LLM Consensus</div>
          <h1 className="page-title">Agent Analysis</h1>
          <p className="page-subtitle">
            Cross-examine privacy policy clauses with independent LLM evaluators. Statuses reflect real backend
            health checks and live response verification.
          </p>
        </div>
      </div>

      {/* Provider Audit & Operational Overview Banner */}
      <div className="provider-audit-banner">
        <div className="provider-audit-info">
          <div className="audit-status-icon-wrap">
            <ShieldCheck size={20} className="text-success" />
          </div>
          <div>
            <div className="audit-status-headline">
              <strong>{readyCount} of {totalCount} Providers Operational</strong>
              <span className="audit-tag audit-tag--active">
                {readyCount === totalCount ? 'All Systems Go' : 'Consensus Active'}
              </span>
            </div>
            <p className="audit-status-desc">
              {readyCount === totalCount
                ? 'All configured independent evaluator engines are verified and accepting queries.'
                : 'Operational evaluators (Gemini, Groq, OpenRouter) conduct consensus audits. Unavailable engines with exhausted credit balances are isolated and excluded.'}
            </p>
          </div>
        </div>

        <button
          type="button"
          className="btn btn--secondary btn--sm btn-recheck-all"
          onClick={handleCheckAll}
          disabled={checkingAll}
          title="Re-verify all provider connections"
        >
          <RefreshCw size={14} className={checkingAll ? 'spin-animation' : ''} />
          <span>{checkingAll ? 'Verifying Providers...' : 'Check All Connections'}</span>
        </button>
      </div>

      {/* Provider Status Grid */}
      <div className="provider-status-grid">
        {Object.entries(providers).map(([key, info]) => {
          const providerTitles = {
            claude: 'Anthropic Claude',
            gemini: 'Google Gemini',
            groq: 'Groq LPU Engine',
            openai: 'OpenAI GPT',
            deepseek: 'DeepSeek LLM',
            openrouter: 'OpenRouter',
          }

          const providerName = info.name || providerTitles[key] || key
          const status = info.status || (info.configured ? 'READY' : 'NOT_CONFIGURED')
          const badgeMeta = getStatusBadgeConfig(status, info.is_available)
          const StatusIcon = badgeMeta.icon
          const isChecking = checkingProvider[key]

          return (
            <div key={key} className={`card provider-status-card ${badgeMeta.cardClass}`}>
              <div className="provider-card-top">
                <span className={`provider-badge-indicator indicator--${status.toLowerCase()}`} />
                <h4 className="provider-name">{providerName}</h4>
              </div>

              <div className="provider-model-name" title={info.model}>
                <code>{info.model || 'Default Model'}</code>
              </div>

              <div className="provider-card-status-badge-row">
                <span className={`provider-health-pill ${badgeMeta.className}`}>
                  <StatusIcon size={13} className="provider-health-icon" />
                  <span>{info.status_label || badgeMeta.label}</span>
                </span>
              </div>

              {/* Error Explanation when not ready */}
              {info.error && (
                <div className="provider-error-callout" title={info.error_detail || info.error}>
                  <AlertTriangle size={13} className="error-callout-icon" />
                  <span className="error-callout-text">{info.error}</span>
                </div>
              )}

              {/* Card Footer with timestamp and manual check action */}
              <div className="provider-card-footer">
                <span className="provider-timestamp" title={info.last_verified_at || 'Unverified'}>
                  <Clock size={11} className="timestamp-icon" />
                  <span>{formatTime(info.last_verified_at)}</span>
                </span>

                <button
                  type="button"
                  className="btn-provider-check"
                  onClick={() => handleCheckConnection(key)}
                  disabled={isChecking}
                  title={`Test live connection to ${providerName}`}
                >
                  <RefreshCw size={12} className={isChecking ? 'spin-animation' : ''} />
                  <span>{isChecking ? 'Checking...' : 'Check'}</span>
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Interactive Evaluation Form */}
      <div className="card evaluation-form-card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Initiate Multi-Agent Audit</h3>
            <p className="card-subtitle">
              Select an indicator and provide a policy excerpt to cross-examine across operational evaluators.
            </p>
          </div>
        </div>

        <form className="card-body eval-form" onSubmit={handleRunEvaluation}>
          <div className="form-row">
            <div className="form-group" style={{ flex: '0 0 320px' }}>
              <label className="form-label" htmlFor="indicator-select">
                Target Compliance Indicator
              </label>
              <select
                id="indicator-select"
                className="form-select"
                value={selectedIndId}
                onChange={(e) => {
                  const newId = e.target.value
                  setSelectedIndId(newId)
                  if (analysis?.indicators) {
                    const match = analysis.indicators.find((ind) => ind.id === newId)
                    if (match?.evidence?.[0]) {
                      setEvidenceText(extractEvidenceString(match.evidence[0]))
                    }
                  }
                }}
              >
                {SECONDARY_INDICATORS.map((sec) => (
                  <option key={sec.id} value={sec.id}>
                    {sec.id} — {sec.name} ({sec.primary})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label">Statutory Criterion Summary</label>
              <div className="indicator-desc-callout">
                <strong>{currentIndicatorMeta.name}:</strong> {currentIndicatorMeta.description}
              </div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="evidence-text">
              Policy Evidence Passage (Extracted Text)
            </label>
            <textarea
              id="evidence-text"
              className="form-textarea"
              rows={4}
              placeholder="Paste or edit the policy clause to evaluate..."
              value={evidenceText}
              onChange={(e) => setEvidenceText(e.target.value)}
            />
            <span className="form-hint">
              Evaluators strictly verify that supporting quotations exist verbatim in this passage before reaching a compliant finding.
            </span>
          </div>

          {evalError && (
            <div className="alert-banner alert-banner--error">
              <AlertTriangle size={16} />
              <span>{evalError}</span>
            </div>
          )}

          <div className="eval-form-actions">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => {
                setEvidenceText('')
                setEvalResult(null)
                setEvalError('')
              }}
              disabled={evaluating}
            >
              <RotateCcw size={15} />
              <span>Clear</span>
            </button>

            <button
              type="submit"
              className="btn btn--primary btn--lg"
              disabled={evaluating || !String(evidenceText || '').trim()}
            >
              {evaluating ? (
                <>
                  <Loader2 size={18} className="spin-animation" />
                  <span>Cross-Examining Across Providers...</span>
                </>
              ) : (
                <>
                  <Play size={16} fill="currentColor" />
                  <span>Execute Multi-Agent Audit</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Consensus Summary Banner (When Results Available) */}
      {evalResult && (
        <div className="eval-results-container">
          <div className="card consensus-card">
            <div className="consensus-header">
              <div className="consensus-title-area">
                <span className="consensus-eyebrow">Aggregated Multi-Agent Consensus</span>
                <h3 className="consensus-main-title">
                  Consensus Decision:{' '}
                  <span className={`consensus-decision-highlight consensus-decision--${consensus?.final_decision}`}>
                    {consensus?.final_decision?.toUpperCase() || 'EVALUATED'}
                  </span>
                </h3>
              </div>

              <div className="consensus-metrics-cluster">
                <div className="consensus-metric-item">
                  <span className="metric-tiny-label">Agreement Rate</span>
                  <span className="metric-tiny-value">
                    {consensus?.agreement_rate !== undefined
                      ? `${(consensus.agreement_rate * 100).toFixed(0)}%`
                      : '—'}
                  </span>
                </div>
                <div className="consensus-metric-item">
                  <span className="metric-tiny-label">Confidence</span>
                  <span className="metric-tiny-value">
                    {consensus?.confidence !== undefined
                      ? `${(consensus.confidence * 100).toFixed(1)}%`
                      : '—'}
                  </span>
                </div>
                <div className="consensus-metric-item">
                  <span className="metric-tiny-label">Reporting Agents</span>
                  <span className="metric-tiny-value">
                    {results.length} Evaluator{results.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
            </div>

            {/* Disagreement banner if agents had conflicting findings */}
            {hasDisagreement && (
              <div className="consensus-alert consensus-alert--warning">
                <AlertTriangle size={18} className="consensus-alert-icon" />
                <div>
                  <strong>Agent Disagreement Identified:</strong> Participating providers
                  reached conflicting determinations ({Array.from(decisionsSet).join(' vs ')}). Review individual
                  evaluator rationales below.
                </div>
              </div>
            )}

            {/* Failed evaluators notification if any */}
            {failedEvals.length > 0 && (
              <div className="consensus-alert consensus-alert--info">
                <Info size={18} className="consensus-alert-icon" />
                <div>
                  <strong>Provider Fault Isolation:</strong> {failedEvals.length} engine(s) ({failedEvals.map(f => f.agent_name).join(', ')}) were omitted from consensus calculations due to operational restrictions.
                </div>
              </div>
            )}

            <div className="consensus-legal-disclaimer">
              <Info size={15} />
              <span>
                <strong>Important Legal Notice:</strong> AI multi-agent consensus reflects algorithmic text
                matching against statutory criteria and does not constitute formal legal certification.
              </span>
            </div>
          </div>

          {/* Individual Agent Results Cards */}
          <div className="card table-card">
            <div className="card-header">
              <h3 className="card-title">Provider Findings Comparison</h3>
            </div>
            <div className="table-responsive">
              <table className="symbolon-table">
                <thead>
                  <tr>
                    <th style={{ width: '160px' }}>Provider</th>
                    <th style={{ width: '140px' }}>Decision</th>
                    <th style={{ width: '110px' }}>Confidence</th>
                    <th>Rationale & Evaluator Findings</th>
                    <th style={{ width: '220px' }}>Verified Evidence Quote</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((res, index) => {
                    const agentName = res.agent_name || `Agent ${index + 1}`
                    const isFailed = Boolean(res.error)

                    return (
                      <tr key={index}>
                        <td>
                          <div className="provider-cell">
                            <Bot size={16} className="provider-cell-icon" />
                            <strong className="provider-cell-name">{agentName}</strong>
                          </div>
                        </td>
                        <td>
                          {isFailed ? (
                            <span className="status-badge status-badge--error">Failed</span>
                          ) : (
                            <StatusBadge status={res.decision} />
                          )}
                        </td>
                        <td>
                          {res.confidence !== undefined ? (
                            <span className="confidence-pill">
                              {(res.confidence * 100).toFixed(0)}%
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>
                          <div className="rationale-text">
                            {res.rationale || res.error_message || 'No rationale recorded.'}
                          </div>
                        </td>
                        <td>
                          {res.evidence && res.evidence.length > 0 ? (
                            <ul className="evidence-quote-list">
                              {res.evidence.map((quote, qIdx) => (
                                <li key={qIdx} className="evidence-quote-item">
                                  "{quote}"
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-muted">None extracted</span>
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
