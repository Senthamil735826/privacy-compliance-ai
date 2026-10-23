import React from 'react'
import {
  UploadCloud,
  BookOpen,
  ShieldCheck,
  Search,
  Sparkles,
  FileText,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  ArrowRight,
} from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { StatusBadge } from '../components/StatusBadge'
import { PRIMARY_CATEGORIES } from '../data/indicatorsData'

export function OverviewView({
  analysis,
  activeDocumentName,
  onNavigate,
  onLoadSample,
}) {
  const summary = analysis?.compliance_summary
  const indicators = analysis?.indicators || []
  const hasAnalysis = Boolean(analysis && indicators.length > 0)

  // Metrics calculation
  const totalIndicators = summary?.total_indicators || 40
  const matchedIndicators = summary?.matched || 0
  const missingIndicators = summary?.not_matched || (hasAnalysis ? totalIndicators - matchedIndicators : 0)
  const coveragePercent = summary?.coverage || (hasAnalysis ? `${Math.round((matchedIndicators / totalIndicators) * 100)}%` : '0%')

  // Group by primary indicator (A1-A7)
  const categoryStats = PRIMARY_CATEGORIES.map((cat) => {
    const catIndicators = indicators.filter((ind) => ind.primary === cat.id)
    const catMatched = catIndicators.filter((ind) => ind.matched).length
    const totalCount = cat.secondaryIds?.length || 0
    return {
      ...cat,
      matched: catMatched,
      total: totalCount,
      rate: totalCount > 0 ? Math.round((catMatched / totalCount) * 100) : 0,
    }
  })

  return (
    <div className="view-container">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div className="page-badge">Enterprise Compliance Intelligence</div>
          <h1 className="page-title">Privacy Intelligence</h1>
          <p className="page-subtitle">
            Understand privacy policies. Identify compliance gaps. Explore verified evidence.
          </p>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => onNavigate('library')}
          >
            <BookOpen size={16} />
            <span>Policy Library</span>
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => onNavigate('analyze')}
          >
            <UploadCloud size={16} />
            <span>Analyze a Policy</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <MetricCard
          title="Active Policy"
          value={activeDocumentName ? '1 Active' : '0 Loaded'}
          subtitle={activeDocumentName || 'No active policy selected'}
          icon={FileText}
          variant="primary"
        />
        <MetricCard
          title="Indicators Evaluated"
          value={hasAnalysis ? `${matchedIndicators}/${totalIndicators}` : '40 Framework'}
          subtitle={hasAnalysis ? `${coveragePercent} detection coverage` : 'A1–A7, B1–B40 defined'}
          icon={CheckCircle}
          variant="success"
        />
        <MetricCard
          title="Potential Compliance Gaps"
          value={hasAnalysis ? missingIndicators : '—'}
          subtitle={hasAnalysis ? 'Required provisions missing in text' : 'Analyze policy to inspect'}
          icon={AlertTriangle}
          variant="warning"
        />
        <MetricCard
          title="Multi-Agent Consensus"
          value="6 Providers"
          subtitle="Claude, Gemini, Groq, OpenAI, DeepSeek, OpenRouter"
          icon={Sparkles}
          variant="indigo"
        />

      </div>

      {/* Main Content Area */}
      {!hasAnalysis ? (
        <div className="overview-empty-state">
          <div className="overview-empty-icon" aria-hidden="true">
            <ShieldCheck size={36} />
          </div>
          <h3 className="overview-empty-title">Ready to Audit Your Privacy Policy</h3>
          <p className="overview-empty-desc">
            Upload a text-based PDF privacy policy to evaluate compliance across 40 statutory indicators,
            extract verifiable evidence quotes, and cross-examine provisions with multi-LLM agents.
          </p>
          <div className="overview-empty-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => onNavigate('analyze')}
            >
              <UploadCloud size={16} />
              <span>Upload PDF Document</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="overview-analysis-grid">
          {/* Category Progress Card */}
          <div className="card overview-card">
            <div className="card-header">
              <div>
                <h3 className="card-title">Statutory Indicator Coverage</h3>
                <p className="card-subtitle">Distribution across 7 Primary Privacy Categories</p>
              </div>
              <button
                type="button"
                className="btn btn--text"
                onClick={() => onNavigate('indicators')}
              >
                <span>View Explorer</span>
                <ArrowRight size={14} />
              </button>
            </div>
            <div className="card-body">
              <div className="category-list">
                {categoryStats.map((cat) => (
                  <div key={cat.id} className="category-item">
                    <div className="category-header">
                      <div className="category-meta">
                        <span className="category-id">{cat.id}</span>
                        <span className="category-name">{cat.name}</span>
                      </div>
                      <span className="category-count">
                        <strong>{cat.matched}</strong> / {cat.total} detected ({cat.rate}%)
                      </span>
                    </div>
                    <div className="category-progress-track">
                      <div
                        className="category-progress-fill"
                        style={{ width: `${cat.rate}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Exploration Hub */}
          <div className="overview-hub-col">
            <div className="card overview-card">
              <div className="card-header">
                <div>
                  <h3 className="card-title">Intelligence Modules</h3>
                  <p className="card-subtitle">Deep dive into analyzed policy findings</p>
                </div>
              </div>
              <div className="card-body hub-actions">
                <div
                  className="hub-action-card"
                  onClick={() => onNavigate('indicators')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="hub-action-icon hub-action-icon--blue">
                    <ShieldCheck size={20} />
                  </div>
                  <div className="hub-action-content">
                    <h4 className="hub-action-title">Indicator Explorer</h4>
                    <p className="hub-action-desc">
                      Examine all 40 statutory requirements and filter by detected vs missing clauses.
                    </p>
                  </div>
                  <ArrowRight size={16} className="hub-action-arrow" />
                </div>

                <div
                  className="hub-action-card"
                  onClick={() => onNavigate('evidence')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="hub-action-icon hub-action-icon--violet">
                    <Search size={20} />
                  </div>
                  <div className="hub-action-content">
                    <h4 className="hub-action-title">Evidence Explorer</h4>
                    <p className="hub-action-desc">
                      Inspect verbatim citations and run semantic search across policy passages.
                    </p>
                  </div>
                  <ArrowRight size={16} className="hub-action-arrow" />
                </div>

                <div
                  className="hub-action-card"
                  onClick={() => onNavigate('agents')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="hub-action-icon hub-action-icon--indigo">
                    <Sparkles size={20} />
                  </div>
                  <div className="hub-action-content">
                    <h4 className="hub-action-title">Multi-Agent Verification</h4>
                    <p className="hub-action-desc">
                      Compare multi-LLM consensus across Claude, Gemini, and Groq with fault isolation.
                    </p>
                  </div>
                  <ArrowRight size={16} className="hub-action-arrow" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
