import React, { useRef, useState } from 'react'
import {
  UploadCloud,
  FileText,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  ShieldAlert,
  Loader2,
  Trash2,
  Search,
  Sparkles,
} from 'lucide-react'
import { StatusBadge } from '../components/StatusBadge'
import { PRIMARY_CATEGORIES } from '../data/indicatorsData'

export function AnalyzePolicyView({
  file,
  onSelectFile,
  onAnalyze,
  loading,
  error,
  analysis,
  onNavigate,
  onReset,
}) {
  const fileInputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  const summary = analysis?.compliance_summary
  const hasAnalysis = Boolean(analysis && summary)

  function handleDragOver(e) {
    e.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave(e) {
    e.preventDefault()
    setIsDragging(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) {
      onSelectFile(droppedFile)
    }
  }

  function handleFileInputChange(e) {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      onSelectFile(selectedFile)
    }
  }

  function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  return (
    <div className="view-container">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div className="page-badge">Document Ingestion & Audit</div>
          <h1 className="page-title">Analyze a Privacy Policy</h1>
          <p className="page-subtitle">
            Upload a text-based policy document to identify statutory indicators, examine verbatim evidence,
            and surface compliance gaps.
          </p>
        </div>
      </div>

      {/* Error alert if any */}
      {error && (
        <div className="alert-banner alert-banner--error" role="alert">
          <AlertCircle size={18} className="alert-banner-icon" />
          <div className="alert-banner-body">
            <strong>Analysis Interrupted:</strong> {error}
          </div>
        </div>
      )}

      {/* Main Upload / Results Card */}
      {!hasAnalysis ? (
        <div className="card upload-card">
          <div
            className={`upload-dropzone ${isDragging ? 'upload-dropzone--dragging' : ''} ${
              file ? 'upload-dropzone--has-file' : ''
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => {
              if (!file && fileInputRef.current) {
                fileInputRef.current.click()
              }
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="sr-only"
              onChange={handleFileInputChange}
            />

            {!file ? (
              <div className="dropzone-content">
                <div className="dropzone-icon" aria-hidden="true">
                  <UploadCloud size={44} />
                </div>
                <h3 className="dropzone-heading">Drop your privacy policy PDF here</h3>
                <p className="dropzone-subheading">
                  Drag and drop a PDF file here, or{' '}
                  <button
                    type="button"
                    className="dropzone-browse-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      fileInputRef.current?.click()
                    }}
                  >
                    browse files
                  </button>
                </p>
                <div className="dropzone-hint">
                  Supports text-based PDF documents up to 25MB. Text extraction and chunking are performed locally by the backend.
                </div>
              </div>
            ) : (
              <div className="dropzone-file-selected" onClick={(e) => e.stopPropagation()}>
                <div className="file-preview-icon" aria-hidden="true">
                  <FileText size={32} />
                </div>
                <div className="file-preview-info">
                  <div className="file-preview-name" title={file.name}>
                    {file.name}
                  </div>
                  <div className="file-preview-meta">
                    <span>{formatFileSize(file.size)}</span>
                    <span className="meta-separator">•</span>
                    <span>Ready for evaluation</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn--icon-danger"
                  onClick={onReset}
                  title="Remove selected file"
                  aria-label="Remove selected file"
                  disabled={loading}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            )}
          </div>

          {/* Action Bar */}
          <div className="upload-actions-bar">
            <div className="upload-disclaimer">
              <ShieldAlert size={15} />
              <span>
                Files are processed securely. Extracted clauses are evaluated against 40 statutory requirements without external training retention.
              </span>
            </div>

            <div className="upload-cta-group">
              {file && !loading && (
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                >
                  Change File
                </button>
              )}
              <button
                type="button"
                className="btn btn--primary btn--lg"
                onClick={onAnalyze}
                disabled={!file || loading}
              >
                {loading ? (
                  <>
                    <Loader2 size={18} className="spin-animation" />
                    <span>Processing Document & Evaluating Indicators...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud size={18} />
                    <span>Start Compliance Analysis</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Analysis Complete Banner & Quick Inspection Hub */
        <div className="analysis-complete-container">
          <div className="card analysis-success-card">
            <div className="analysis-success-header">
              <div className="analysis-success-badge">
                <CheckCircle2 size={18} />
                <span>Analysis Complete</span>
              </div>
              <button
                type="button"
                className="btn btn--outline-sm"
                onClick={onReset}
              >
                Analyze Another Policy
              </button>
            </div>

            <div className="analysis-summary-content">
              <div className="analysis-doc-title-row">
                <FileText size={24} className="doc-icon" />
                <div>
                  <h2 className="analysis-doc-name">{file?.name || 'Uploaded Privacy Policy'}</h2>
                  <p className="analysis-doc-caption">
                    Document parsed into {analysis?.chunks?.length || 'semantic'} text chunks. 40 statutory indicators evaluated.
                  </p>
                </div>
              </div>

              {/* Statutory coverage pill banner */}
              <div className="analysis-stat-row">
                <div className="analysis-stat-item">
                  <span className="stat-label">Coverage Score</span>
                  <span className="stat-value stat-value--highlight">
                    {summary?.coverage || '0%'}
                  </span>
                  <span className="stat-note">Statutory detection rate</span>
                </div>
                <div className="analysis-stat-item">
                  <span className="stat-label">Detected Provisions</span>
                  <span className="stat-value stat-value--success">
                    {summary?.matched || 0}
                  </span>
                  <span className="stat-note">Satisfied criteria</span>
                </div>
                <div className="analysis-stat-item">
                  <span className="stat-label">Potential Gaps</span>
                  <span className="stat-value stat-value--warning">
                    {summary?.not_matched || 0}
                  </span>
                  <span className="stat-note">Clauses not identified</span>
                </div>
                <div className="analysis-stat-item">
                  <span className="stat-label">Total Indicator Scope</span>
                  <span className="stat-value">
                    {summary?.total_indicators || 40}
                  </span>
                  <span className="stat-note">A1–A7 Framework</span>
                </div>
              </div>
            </div>

            {/* Direct Workflow Navigation */}
            <div className="analysis-next-steps">
              <h3 className="next-steps-title">Recommended Review Next Steps</h3>
              <div className="next-steps-grid">
                <div
                  className="next-step-card"
                  onClick={() => onNavigate('indicators')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="next-step-icon">
                    <CheckCircle2 size={20} />
                  </div>
                  <div className="next-step-body">
                    <h4 className="next-step-name">Indicator Explorer</h4>
                    <p className="next-step-desc">
                      Review all 40 indicators, inspect detected clauses vs missing requirements.
                    </p>
                  </div>
                  <ArrowRight size={16} className="next-step-arrow" />
                </div>

                <div
                  className="next-step-card"
                  onClick={() => onNavigate('evidence')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="next-step-icon next-step-icon--violet">
                    <Search size={20} />
                  </div>
                  <div className="next-step-body">
                    <h4 className="next-step-name">Evidence Explorer</h4>
                    <p className="next-step-desc">
                      Examine verbatim policy excerpts and run semantic search across chunks.
                    </p>
                  </div>
                  <ArrowRight size={16} className="next-step-arrow" />
                </div>

                <div
                  className="next-step-card"
                  onClick={() => onNavigate('agents')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="next-step-icon next-step-icon--indigo">
                    <Sparkles size={20} />
                  </div>
                  <div className="next-step-body">
                    <h4 className="next-step-name">Multi-Agent Verification</h4>
                    <p className="next-step-desc">
                      Cross-examine provisions with Claude, Gemini, Groq, and consensus aggregation.
                    </p>
                  </div>
                  <ArrowRight size={16} className="next-step-arrow" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Statutory Framework Reference Section */}
      <div className="upload-guidelines-card card">
        <h3 className="guidelines-title">Statutory Evaluation Scope</h3>
        <p className="guidelines-desc">
          Symbolon Law audits uploaded policies against the comprehensive statutory indicator framework:
        </p>
        <div className="guidelines-grid">
          {PRIMARY_CATEGORIES.map((cat) => (
            <div key={cat.id} className="guideline-item">
              <span className="guideline-tag">{cat.id}</span>
              <strong>{cat.name}:</strong> {cat.description}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
