import React, { useEffect, useState } from 'react'
import {
  Settings,
  Server,
  Shield,
  Key,
  Database,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Info,
} from 'lucide-react'

export function SettingsView({ apiOnline }) {
  const [agentStatus, setAgentStatus] = useState(null)
  const [checking, setChecking] = useState(false)

  async function checkHealth() {
    setChecking(true)
    try {
      const res = await fetch('/api/agents/status')
      if (res.ok) {
        const data = await res.json()
        setAgentStatus(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => {
    checkHealth()
  }, [])

  const providers = agentStatus?.providers || {}

  return (
    <div className="view-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div className="page-badge">Platform Architecture</div>
          <h1 className="page-title">Platform Settings</h1>
          <p className="page-subtitle">
            System configuration, multi-agent evaluation backends, and statutory governance parameters.
          </p>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={checkHealth}
            disabled={checking}
          >
            <RefreshCw size={15} className={checking ? 'spin-animation' : ''} />
            <span>Refresh Connectivity</span>
          </button>
        </div>
      </div>

      <div className="settings-grid">
        {/* Backend & Connectivity Card */}
        <div className="card settings-card">
          <div className="card-header">
            <div className="settings-card-icon">
              <Server size={20} />
            </div>
            <div>
              <h3 className="card-title">Backend Connectivity</h3>
              <p className="card-subtitle">FastAPI integration layer status</p>
            </div>
          </div>
          <div className="card-body">
            <div className="settings-row">
              <span className="settings-label">API Gateway</span>
              <span className="settings-value code-pill">/api (Vite Proxy → 127.0.0.1:8000)</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Gateway Status</span>
              <span className={`settings-status-pill ${apiOnline ? 'text-success' : 'text-danger'}`}>
                {apiOnline ? (
                  <>
                    <CheckCircle2 size={14} /> Connected & Operational
                  </>
                ) : (
                  <>
                    <AlertCircle size={14} /> Offline / Connecting
                  </>
                )}
              </span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Ingestion Engine</span>
              <span className="settings-value">pdfplumber Text Extractor + Semantic Chunker</span>
            </div>
          </div>
        </div>

        {/* Multi-LLM Provider Status Card */}
        <div className="card settings-card">
          <div className="card-header">
            <div className="settings-card-icon">
              <Key size={20} />
            </div>
            <div>
              <h3 className="card-title">Multi-LLM Evaluator Pool</h3>
              <p className="card-subtitle">6 configured consensus providers</p>
            </div>
          </div>
          <div className="card-body">
            <div className="settings-providers-list">
              {Object.entries({
                claude: { name: 'Anthropic Claude', defaultModel: 'claude-3-7-sonnet-20250219' },
                gemini: { name: 'Google Gemini', defaultModel: 'gemini-2.5-flash' },
                groq: { name: 'Groq LPU Engine', defaultModel: 'openai/gpt-oss-20b' },
                openai: { name: 'OpenAI GPT', defaultModel: 'gpt-4.1-mini' },
                deepseek: { name: 'DeepSeek LLM', defaultModel: 'deepseek-chat' },
                openrouter: { name: 'OpenRouter', defaultModel: 'openai/gpt-4o-mini' },
              }).map(([key, meta]) => {

                const live = providers[key]
                const isConfigured = Boolean(live?.configured)
                const model = live?.model || meta.defaultModel

                return (
                  <div key={key} className="settings-provider-row">
                    <div className="provider-info-cell">
                      <strong className="provider-display-name">{meta.name}</strong>
                      <span className="provider-model-code">{model}</span>
                    </div>
                    <div>
                      {live?.status === 'READY' && (
                        <span className="badge-configured">Ready</span>
                      )}
                      {live?.status === 'INSUFFICIENT_BALANCE' && (
                        <span className="badge-balance">Insufficient Balance</span>
                      )}
                      {live?.status === 'AUTH_ERROR' && (
                        <span className="badge-error">Auth Failed</span>
                      )}
                      {(!live?.status || live?.status === 'NOT_CONFIGURED') && (
                        <span className="badge-unconfigured">Not Configured</span>
                      )}
                      {live?.status && !['READY', 'INSUFFICIENT_BALANCE', 'AUTH_ERROR', 'NOT_CONFIGURED'].includes(live.status) && (
                        <span className="badge-unconfigured">{live.status_label || live.status}</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Statutory Framework Reference */}
        <div className="card settings-card" style={{ gridColumn: '1 / -1' }}>
          <div className="card-header">
            <div className="settings-card-icon">
              <Shield size={20} />
            </div>
            <div>
              <h3 className="card-title">Statutory Governance & Disclaimers</h3>
              <p className="card-subtitle">Methodology and compliance definitions</p>
            </div>
          </div>
          <div className="card-body">
            <div className="disclaimer-callout">
              <Info size={18} className="disclaimer-callout-icon" />
              <div className="disclaimer-callout-text">
                <p>
                  <strong>Symbolon Law</strong> provides automated statutory policy parsing, verbatim citation retrieval,
                  and multi-agent natural language cross-examination. Findings reflect presence or absence of prescribed
                  contractual and disclosure provisions under regulatory privacy frameworks.
                </p>
                <p style={{ marginTop: '8px' }}>
                  Automated indicators and consensus determinations do not replace independent legal counsel or guarantee
                  formal regulatory certification.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
