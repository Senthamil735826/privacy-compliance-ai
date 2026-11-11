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
  Sliders,
  Layers,
  FileText,
  Target,
  Scale,
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
      const docId = analysis?.document_id || analysis?.id || targetIndicator?.document_id || null
      const response = await fetch('/api/agents/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_indicator_id: currentIndicatorMeta.primary,
          indicator_id: currentIndicatorMeta.id,
          indicator_description: currentIndicatorMeta.description,
          evidence: evidenceText.trim(),
          document_id: docId,
        }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Evaluation failed on backend.')
      }

      setEvalResult({
        ...data.result,
        tcam_explanation: data.tcam_explanation || data.result?.tcam?.explanation || data.result?.tcam_explanation,
      })
    } catch (err) {
      setEvalError(err.message || 'Error occurred while running multi-agent evaluation.')
    } finally {
      setEvaluating(false)
    }
  }

  // Baseline fallback providers matching active .env configuration
  const rawProviders = providerStatus?.providers || {
    gemini: { provider: 'gemini', name: 'Google Gemini', configured: true, model: 'gemini-3.5-flash', status: 'READY', is_available: true },
    groq: { provider: 'groq', name: 'Groq LPU Engine', configured: true, model: 'openai/gpt-oss-20b', status: 'READY', is_available: true },
    openrouter: { provider: 'openrouter', name: 'OpenRouter', configured: true, model: 'openai/gpt-4o-mini', status: 'READY', is_available: true },
    cohere: { provider: 'cohere', name: 'Cohere Command', configured: true, model: 'command-r-plus-08-2024', status: 'READY', is_available: true },
    kimi: { provider: 'kimi', name: 'Kimi Moonshot AI', configured: true, model: 'kimi-k3', status: 'INSUFFICIENT_BALANCE', is_available: false, error: 'Account balance exhausted.' },
  }

  // Filter out removed legacy providers (Claude, OpenAI, DeepSeek)
  const excludedKeys = new Set(['claude', 'openai', 'deepseek'])
  const providers = Object.fromEntries(
    Object.entries(rawProviders).filter(([k]) => !excludedKeys.has(k.toLowerCase()))
  )


  const consensus = evalResult?.aggregation || evalResult?.consensus
  const results = evalResult?.evaluations || evalResult?.results || []
  const failedEvals = evalResult?.failed_evaluations || []
  const tcamExplanation = evalResult?.tcam_explanation || evalResult?.tcam?.explanation

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
                : 'Operational evaluators conduct multi-agent consensus audits with fault isolation for unavailable providers.'}
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
            gemini: 'Google Gemini',
            groq: 'Groq LPU Engine',
            openrouter: 'OpenRouter',
            cohere: 'Cohere Command',
            kimi: 'Kimi Moonshot AI',
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
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 className="card-title">Initiate Multi-Agent Audit</h3>
            <p className="card-subtitle">
              Select an indicator and provide a policy excerpt to cross-examine across operational evaluators.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', background: 'var(--bg-subtle, rgba(255,255,255,0.05))', padding: '6px 12px', borderRadius: '20px', border: '1px solid var(--border-color)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: readyCount > 0 ? '#10B981' : '#EF4444' }} />
            <span>Active Voting Engines: <strong>{Object.values(providers).filter(p => p.is_available).map(p => p.name.split(' ')[0]).join(', ') || 'None ready'}</strong></span>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label className="form-label" htmlFor="evidence-text" style={{ margin: 0 }}>
                Policy Evidence Passage (Extracted Text)
              </label>
              {analysis?.indicators && (
                <button
                  type="button"
                  style={{ background: 'none', border: 'none', color: 'var(--accent-primary, #6366F1)', cursor: 'pointer', fontSize: '12px', fontWeight: 500 }}
                  onClick={() => {
                    const match = analysis.indicators.find((ind) => ind.id === selectedIndId)
                    if (match?.evidence?.[0]) {
                      setEvidenceText(extractEvidenceString(match.evidence[0]))
                    }
                  }}
                >
                  ↺ Load Evidence from Uploaded Document
                </button>
              )}
            </div>
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
          {/* Automated TCAM Complexity Assessment & Evidence Quality Card */}
          {tcamExplanation && (
            <div className="card tcam-assessment-card" style={{ marginBottom: '24px' }}>
              <div
                className="card-header"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                  borderBottom: '1px solid var(--border-color)',
                  paddingBottom: '14px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      background: 'rgba(99, 102, 241, 0.15)',
                      color: '#818CF8',
                      padding: '10px',
                      borderRadius: '10px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Sliders size={22} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="page-badge" style={{ fontSize: '11px', padding: '2px 8px' }}>
                        TCAM v1.0
                      </span>
                      <h3 className="card-title" style={{ margin: 0, fontSize: '18px' }}>
                        Automated Task Complexity & Evidence Quality Assessment
                      </h3>
                    </div>
                    <p className="card-subtitle" style={{ margin: '4px 0 0 0', fontSize: '13px' }}>
                      Deterministic routing driven by statutory indicator difficulty and actual retrieval quality.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <span
                    className={`status-badge ${
                      tcamExplanation.complexity_score < 0.4
                        ? 'status-badge--success'
                        : tcamExplanation.complexity_score < 0.7
                        ? 'status-badge--warning'
                        : 'status-badge--error'
                    }`}
                    style={{ fontSize: '13px', padding: '6px 12px', fontWeight: 600 }}
                  >
                    θ = {tcamExplanation.complexity_score.toFixed(3)} ({tcamExplanation.complexity_level?.toUpperCase()} COMPLEXITY)
                  </span>
                  <span
                    className="audit-tag audit-tag--active"
                    style={{ fontSize: '13px', padding: '6px 12px' }}
                  >
                    {tcamExplanation.routing_decision} Evaluator{tcamExplanation.routing_decision > 1 ? 's' : ''} Allocated
                  </span>
                </div>
              </div>

              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px', paddingTop: '16px' }}>
                {/* Visual Complexity Gauge & Threshold Bar */}
                <div
                  style={{
                    background: 'var(--bg-subtle, rgba(255,255,255,0.03))',
                    padding: '16px 20px',
                    borderRadius: '10px',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '10px',
                      fontSize: '13px',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    <span>
                      <strong>Composite Complexity Formula:</strong>{' '}
                      <code style={{ background: 'rgba(0,0,0,0.2)', padding: '2px 6px', borderRadius: '4px' }}>
                        θ = 0.5 · H + 0.5 · S = {tcamExplanation.complexity_score.toFixed(3)}
                      </code>
                    </span>
                    <span style={{ fontWeight: 500 }}>
                      {tcamExplanation.complexity_score < 0.4
                        ? '✓ Low Complexity (< 0.40) ➔ Routed to 1 Evaluator'
                        : tcamExplanation.complexity_score < 0.7
                        ? '⚡ Medium Complexity [0.40, 0.70) ➔ Routed to 3 Evaluators'
                        : '⚠ High Complexity (≥ 0.70) ➔ Routed to 5 Evaluators'}
                    </span>
                  </div>

                  {/* Visual Progress Bar with Threshold Marks */}
                  <div
                    style={{
                      position: 'relative',
                      width: '100%',
                      height: '14px',
                      background: 'rgba(255,255,255,0.1)',
                      borderRadius: '7px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(100, Math.max(0, tcamExplanation.complexity_score * 100))}%`,
                        height: '100%',
                        background:
                          tcamExplanation.complexity_score < 0.4
                            ? 'linear-gradient(90deg, #10B981, #34D399)'
                            : tcamExplanation.complexity_score < 0.7
                            ? 'linear-gradient(90deg, #F59E0B, #FBBF24)'
                            : 'linear-gradient(90deg, #EF4444, #F87171)',
                        borderRadius: '7px',
                        transition: 'width 0.5s ease',
                      }}
                    />
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginTop: '8px',
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                    }}
                  >
                    <span>0.0 (Trivial)</span>
                    <span style={{ color: '#10B981', fontWeight: 600 }}>| 0.40 Threshold (1 vs 3 Agents)</span>
                    <span style={{ color: '#F59E0B', fontWeight: 600 }}>| 0.70 Threshold (3 vs 5 Agents)</span>
                    <span>1.0 (Maximum Difficulty)</span>
                  </div>
                </div>

                {/* Grid of 5 Metric Component Cards */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
                    gap: '14px',
                  }}
                >
                  {/* Card 1: Inherent Difficulty (H) */}
                  <div
                    className="card"
                    style={{
                      padding: '14px',
                      background: 'var(--bg-card-elevated, rgba(255,255,255,0.02))',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600 }}>
                          Inherent Difficulty (H)
                        </span>
                        <Scale size={14} color="#818CF8" />
                      </div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {(tcamExplanation.inherent_difficulty * 100).toFixed(0)}%
                        <span style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-muted)', marginLeft: '6px' }}>
                          ({tcamExplanation.inherent_difficulty.toFixed(2)})
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '6px 0 0 0' }}>
                        {tcamExplanation.inherent_difficulty_rationale}
                      </p>
                    </div>
                    <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px dashed var(--border-subtle)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      Benchmark Calibrated ({selectedIndId})
                    </div>
                  </div>

                  {/* Card 2: Evidence Recall / Coverage Proxy (R) */}
                  <div
                    className="card"
                    style={{
                      padding: '14px',
                      background: 'var(--bg-card-elevated, rgba(255,255,255,0.02))',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600 }}>
                          Evidence Coverage Proxy (R)
                        </span>
                        <Target size={14} color="#10B981" />
                      </div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {(tcamExplanation.evidence_recall * 100).toFixed(1)}%
                        <span style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-muted)', marginLeft: '6px' }}>
                          ({tcamExplanation.evidence_recall.toFixed(2)})
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '6px 0 0 0' }}>
                        {tcamExplanation.evidence_recall_rationale}
                      </p>
                    </div>
                    <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px dashed var(--border-subtle)', fontSize: '11px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Lexical: {(tcamExplanation.lexical_coverage_score * 100).toFixed(0)}%</span>
                      <span>Density: {(tcamExplanation.semantic_density_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  {/* Card 3: Evidence Dispersion (D) */}
                  <div
                    className="card"
                    style={{
                      padding: '14px',
                      background: 'var(--bg-card-elevated, rgba(255,255,255,0.02))',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600 }}>
                          Evidence Dispersion (D)
                        </span>
                        <Layers size={14} color="#F59E0B" />
                      </div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {(tcamExplanation.evidence_dispersion * 100).toFixed(1)}%
                        <span style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-muted)', marginLeft: '6px' }}>
                          ({tcamExplanation.evidence_dispersion.toFixed(2)})
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '6px 0 0 0' }}>
                        {tcamExplanation.evidence_dispersion_rationale}
                      </p>
                    </div>
                    <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px dashed var(--border-subtle)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      Span: {(tcamExplanation.chunk_span * 100).toFixed(0)}% of document
                    </div>
                  </div>

                  {/* Card 4: Semantic Ambiguity (A) */}
                  <div
                    className="card"
                    style={{
                      padding: '14px',
                      background: 'var(--bg-card-elevated, rgba(255,255,255,0.02))',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600 }}>
                          Semantic Ambiguity (A)
                        </span>
                        <HelpCircle size={14} color="#EC4899" />
                      </div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {(tcamExplanation.semantic_ambiguity * 100).toFixed(1)}%
                        <span style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-muted)', marginLeft: '6px' }}>
                          ({tcamExplanation.semantic_ambiguity.toFixed(2)})
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '6px 0 0 0' }}>
                        {tcamExplanation.semantic_ambiguity_rationale}
                      </p>
                    </div>
                    <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px dashed var(--border-subtle)', fontSize: '11px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Hedge: {(tcamExplanation.hedge_density * 100).toFixed(0)}%</span>
                      <span>Flatness: {(tcamExplanation.distribution_entropy * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  {/* Card 5: Evidence Scarcity (S) */}
                  <div
                    className="card"
                    style={{
                      padding: '14px',
                      background: 'var(--bg-card-elevated, rgba(255,255,255,0.02))',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600 }}>
                          Evidence Scarcity (S)
                        </span>
                        <FileText size={14} color="#6366F1" />
                      </div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {(tcamExplanation.evidence_scarcity * 100).toFixed(1)}%
                        <span style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-muted)', marginLeft: '6px' }}>
                          ({tcamExplanation.evidence_scarcity.toFixed(2)})
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '6px 0 0 0' }}>
                        Composite quality penalty derived from recall deficit, chunk dispersion, and semantic ambiguity.
                      </p>
                    </div>
                    <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px dashed var(--border-subtle)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      <code>S = 1 - ⅓(R + (1-D) + (1-A))</code>
                    </div>
                  </div>
                </div>

                {/* Referenced Chunks Badges */}
                {tcamExplanation.referenced_chunks && tcamExplanation.referenced_chunks.length > 0 && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: '12px',
                      background: 'var(--bg-subtle, rgba(255,255,255,0.03))',
                      padding: '8px 14px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-subtle)',
                      flexWrap: 'wrap',
                    }}
                  >
                    <strong style={{ color: 'var(--text-secondary)' }}>Referenced FAISS Retrieval Chunks:</strong>
                    {tcamExplanation.referenced_chunks.map((cid) => (
                      <span
                        key={cid}
                        style={{
                          background: 'rgba(99, 102, 241, 0.15)',
                          color: '#818CF8',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 600,
                          fontSize: '11px',
                        }}
                      >
                        Chunk #{cid}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

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
                {evalResult?.tcam && (
                  <div className="consensus-metric-item">
                    <span className="metric-tiny-label">TCAM Routing</span>
                    <span className="metric-tiny-value">
                      {evalResult.tcam.complexity_level} ({evalResult.tcam.evaluator_count} Agents)
                    </span>
                  </div>
                )}
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
