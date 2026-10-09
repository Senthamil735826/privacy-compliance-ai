import { useMemo, useRef, useState } from 'react'
import './App.css'

function App() {
  const fileInputRef = useRef(null)

  const [file, setFile] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [dragging, setDragging] = useState(false)

  const summary = analysis?.compliance_summary

  // Keep the array reference stable to satisfy React's exhaustive-deps rule.
  const indicators = useMemo(
    () => analysis?.indicators ?? [],
    [analysis],
  )

  // Filter indicators by status, ID, name, or primary category.
  const filteredIndicators = useMemo(() => {
    return indicators.filter((indicator) => {
      const matchesFilter =
        filter === 'all' ||
        (filter === 'found' && indicator.matched) ||
        (filter === 'missing' && !indicator.matched)

      const query = search.trim().toLowerCase()

      const matchesSearch =
        !query ||
        indicator.id.toLowerCase().includes(query) ||
        indicator.name.toLowerCase().includes(query) ||
        (indicator.primary ?? '').toLowerCase().includes(query)

      return matchesFilter && matchesSearch
    })
  }, [indicators, filter, search])

  // Validate and select a PDF file.
  function selectFile(selectedFile) {
    if (!selectedFile) return

    setError('')

    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a PDF file.')
      return
    }

    if (selectedFile.size === 0) {
      setError('The selected file is empty.')
      return
    }

    setFile(selectedFile)
    setAnalysis(null)
  }

  // Upload the PDF to the FastAPI backend and display the results.
  async function handleAnalyze() {
    if (!file) {
      setError('Select a privacy policy PDF before starting analysis.')
      return
    }

    setLoading(true)
    setError('')
    setAnalysis(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/policy/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'The server could not process the PDF.',
        )
      }

      if (
        data.status !== 'success' ||
        !Array.isArray(data.indicators) ||
        !data.compliance_summary
      ) {
        throw new Error('The server returned an unexpected response.')
      }

      setAnalysis(data)
      setFilter('all')
      setSearch('')

      window.setTimeout(() => {
        document
          .getElementById('analysis-results')
          ?.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
          })
      }, 100)
    } catch (err) {
      setError(
        err.message ||
          'Unable to connect to the backend. Check that FastAPI is running.',
      )
    } finally {
      setLoading(false)
    }
  }

  // Handle drag-and-drop PDF uploads.
  function handleDrop(event) {
    event.preventDefault()
    setDragging(false)
    selectFile(event.dataTransfer.files?.[0])
  }

  const coverage = Number(summary?.coverage ?? 0)
  const matched = Number(summary?.matched ?? 0)
  const total = Number(summary?.total_indicators ?? 40)
  const notMatched = Number(summary?.not_matched ?? 0)

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <a href="#overview" className="brand">
          <span className="brand-mark">P</span>

          <span className="brand-copy">
            <strong>PrivAI</strong>
            <small>COMPLIANCE INTELLIGENCE</small>
          </span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="navigation">
          <a className="nav-link active" href="#overview">
            <span className="nav-icon">◫</span>
            Overview
          </a>

          <a className="nav-link" href="#upload">
            <span className="nav-icon">⇧</span>
            Policy analysis
          </a>

          <a className="nav-link" href="#analysis-results">
            <span className="nav-icon">☷</span>
            Indicator results
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="security-badge">
            <div className="security-icon">✓</div>

            <div>
              <strong>Local API</strong>
              <p>Development environment</p>
            </div>

            <span className="online-dot" />
          </div>

          <div className="sidebar-footer">
            <span className="footer-logo">P</span>

            <div>
              <strong>Privacy Compliance AI</strong>
              <small>Phase 1 · Rule-based engine</small>
            </div>
          </div>
        </div>
      </aside>

      {/* Main dashboard */}
      <main className="main-content" id="overview">
        {/* Header */}
        <header className="topbar">
          <div>
            <div className="breadcrumb">Workspace / Overview</div>
            <h1>Privacy Compliance Dashboard</h1>
          </div>

          <div className="api-status">
            <span className="online-dot" />
            <span>Development mode</span>
          </div>
        </header>

        {/* Welcome banner */}
        <section className="welcome-section">
          <div>
            <div className="eyebrow">
              <span className="eyebrow-dot" />
              PRIVACY INTELLIGENCE PLATFORM
            </div>

            <h2>
              Understand your policy.
              <br />
              <span>Discover what&apos;s missing.</span>
            </h2>

            <p>
              Analyze privacy policies against 40 configured indicators
              and explore the evidence behind each detected requirement.
            </p>
          </div>

          <div className="hero-decoration" aria-hidden="true">
            <div className="hero-orbit orbit-one" />
            <div className="hero-orbit orbit-two" />

            <div className="hero-shield">
              <span>✓</span>
            </div>

            <div className="floating-chip chip-one">
              40 indicators
            </div>

            <div className="floating-chip chip-two">
              PDF analysis
            </div>
          </div>
        </section>

        {/* Summary cards */}
        <section
          className="metrics-grid"
          aria-label="Analysis summary"
        >
          <article className="metric-card">
            <div className="metric-top">
              <span className="metric-icon purple">◉</span>
              <span className="metric-caption">
                OVERALL COVERAGE
              </span>
            </div>

            <div className="metric-value">
              {summary ? `${coverage}%` : '—'}
            </div>

            <div className="metric-bottom">
              <span className="metric-muted">
                {summary ? 'Current document' : 'Awaiting analysis'}
              </span>
            </div>

            <div className="metric-progress">
              <span
                style={{
                  width: `${Math.min(
                    100,
                    Math.max(0, coverage),
                  )}%`,
                }}
              />
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span className="metric-icon green">✓</span>
              <span className="metric-caption">DETECTED</span>
            </div>

            <div className="metric-value">
              {summary ? matched : '—'}

              <span className="metric-denominator">
                {summary ? ` / ${total}` : ''}
              </span>
            </div>

            <div className="metric-bottom">
              <span className="status-text green-text">
                Detected indicators
              </span>
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span className="metric-icon orange">!</span>
              <span className="metric-caption">NOT DETECTED</span>
            </div>

            <div className="metric-value">
              {summary ? notMatched : '—'}
            </div>

            <div className="metric-bottom">
              <span className="metric-muted">
                Requires review
              </span>
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span className="metric-icon blue">▤</span>
              <span className="metric-caption">DOCUMENT PAGES</span>
            </div>

            <div className="metric-value">
              {analysis ? analysis.document.total_pages : '—'}
            </div>

            <div className="metric-bottom">
              <span className="metric-muted">
                {analysis
                  ? `${analysis.document.total_chunks} text chunks`
                  : 'No document processed'}
              </span>
            </div>
          </article>
        </section>

        {/* Upload and analysis pipeline */}
        <section className="workspace-grid">
          <article className="panel upload-panel" id="upload">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">STEP 01</span>
                <h3>Upload a privacy policy</h3>
                <p>Select a PDF document to begin analysis.</p>
              </div>

              <div className="panel-heading-icon">↑</div>
            </div>

            <div
              className={`dropzone ${dragging ? 'dragging' : ''} ${
                file ? 'has-file' : ''
              }`}
              onDragOver={(event) => {
                event.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' ||
                  event.key === ' '
                ) {
                  event.preventDefault()
                  fileInputRef.current?.click()
                }
              }}
              role="button"
              tabIndex={0}
              aria-label="Choose a PDF file"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                hidden
                onChange={(event) => {
                  selectFile(event.target.files?.[0])
                  event.target.value = ''
                }}
              />

              <div className="upload-icon">
                <span>↑</span>
              </div>

              {file ? (
                <>
                  <h4>{file.name}</h4>
                  <p>
                    {(file.size / 1024).toFixed(1)} KB · Ready for analysis
                  </p>
                </>
              ) : (
                <>
                  <h4>Drop your PDF here</h4>
                  <p>or click to browse your files</p>

                  <span className="file-format">
                    PDF DOCUMENTS ONLY
                  </span>
                </>
              )}
            </div>

            <button
              className="primary-button"
              onClick={handleAnalyze}
              disabled={!file || loading}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  Analyzing policy...
                </>
              ) : (
                <>
                  Analyze document
                  <span className="button-arrow">→</span>
                </>
              )}
            </button>

            {error && (
              <div className="error-message" role="alert">
                <span>!</span>
                {error}
              </div>
            )}

            <div className="privacy-note">
              <span>◆</span>

              <p>
                Your PDF is processed by your local development backend.
                This interface does not upload it to a third-party AI
                service.
              </p>
            </div>
          </article>

          <article className="panel process-panel">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">HOW IT WORKS</span>
                <h3>Analysis pipeline</h3>
                <p>From document to indicator results.</p>
              </div>
            </div>

            <div className="pipeline">
              <div className="pipeline-step">
                <div className="pipeline-icon purple-bg">
                  PDF
                </div>

                <div className="pipeline-copy">
                  <strong>Document ingestion</strong>
                  <p>Upload and extract PDF text</p>
                </div>

                <span className="pipeline-check">✓</span>
              </div>

              <div className="pipeline-connector" />

              <div className="pipeline-step">
                <div className="pipeline-icon blue-bg">
                  TXT
                </div>

                <div className="pipeline-copy">
                  <strong>Text processing</strong>
                  <p>Clean and split the document</p>
                </div>

                <span className="pipeline-check">✓</span>
              </div>

              <div className="pipeline-connector" />

              <div className="pipeline-step">
                <div className="pipeline-icon green-bg">
                  40
                </div>

                <div className="pipeline-copy">
                  <strong>Indicator engine</strong>
                  <p>Evaluate configured privacy rules</p>
                </div>

                <span className="pipeline-check">✓</span>
              </div>

              <div className="pipeline-connector" />

              <div className="pipeline-step">
                <div className="pipeline-icon orange-bg">↗</div>

                <div className="pipeline-copy">
                  <strong>Results and evidence</strong>
                  <p>Review matches and missing indicators</p>
                </div>

                <span className="pipeline-pending">4</span>
              </div>
            </div>

            <div className="method-note">
              <strong>Current analysis method</strong>

              <p>
                Keyword-based rules with evidence extraction.
                Results require human review and do not establish
                legal compliance.
              </p>
            </div>
          </article>
        </section>

        {/* Indicator results */}
        <section className="results-section" id="analysis-results">
          <div className="results-heading">
            <div>
              <span className="section-kicker">STEP 02</span>
              <h3>Indicator analysis</h3>

              <p>
                {analysis
                  ? `${filteredIndicators.length} of ${indicators.length} indicators displayed`
                  : 'Upload and analyze a policy to see the results.'}
              </p>
            </div>

            <div className="results-tag">
              <span className="results-tag-dot" />

              {analysis
                ? 'Analysis complete'
                : 'Awaiting document'}
            </div>
          </div>

          {analysis && (
            <>
              <div className="results-toolbar">
                <div className="search-box">
                  <span>⌕</span>

                  <input
                    type="search"
                    placeholder="Search by ID or indicator name..."
                    value={search}
                    onChange={(event) =>
                      setSearch(event.target.value)
                    }
                    aria-label="Search indicators"
                  />
                </div>

                <div className="filter-buttons">
                  <button
                    className={
                      filter === 'all' ? 'selected' : ''
                    }
                    onClick={() => setFilter('all')}
                  >
                    All ({indicators.length})
                  </button>

                  <button
                    className={
                      filter === 'found' ? 'selected' : ''
                    }
                    onClick={() => setFilter('found')}
                  >
                    Detected ({matched})
                  </button>

                  <button
                    className={
                      filter === 'missing' ? 'selected' : ''
                    }
                    onClick={() => setFilter('missing')}
                  >
                    Not detected ({notMatched})
                  </button>
                </div>
              </div>

              <div className="indicator-table-wrap">
                <table className="indicator-table">
                  <thead>
                    <tr>
                      <th>INDICATOR</th>
                      <th>CATEGORY</th>
                      <th>STATUS</th>
                      <th>EVIDENCE</th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredIndicators.map((indicator) => (
                      <tr key={indicator.id}>
                        <td>
                          <div className="indicator-name-cell">
                            <span className="indicator-id">
                              {indicator.id}
                            </span>

                            <div>
                              <strong>{indicator.name}</strong>
                              <small>{indicator.primary}</small>
                            </div>
                          </div>
                        </td>

                        <td>
                          <span className="category-label">
                            {indicator.primary}
                          </span>
                        </td>

                        <td>
                          <span
                            className={`status-pill ${
                              indicator.matched
                                ? 'detected'
                                : 'missing'
                            }`}
                          >
                            <span className="status-pill-dot" />

                            {indicator.matched
                              ? 'Detected'
                              : 'Not detected'}
                          </span>
                        </td>

                        <td>
                          {indicator.evidence?.length > 0 ? (
                            <details className="evidence-details">
                              <summary>
                                View evidence (
                                {indicator.evidence.length})
                              </summary>

                              <div className="evidence-list">
                                {indicator.evidence.map(
                                  (item, index) => (
                                    <div
                                      className="evidence-item"
                                      key={`${indicator.id}-${index}`}
                                    >
                                      <div className="evidence-meta">
                                        <span>
                                          {item.matched_by || 'MATCH'}
                                        </span>

                                        <span>
                                          {item.evidence_type ||
                                            'evidence'}
                                        </span>
                                      </div>

                                      <p>{item.text}</p>

                                      {item.matches?.length > 0 && (
                                        <div className="keyword-list">
                                          {item.matches.map(
                                            (keyword) => (
                                              <span key={keyword}>
                                                {keyword}
                                              </span>
                                            ),
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  ),
                                )}
                              </div>
                            </details>
                          ) : (
                            <span className="no-evidence">
                              No evidence found
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}

                    {filteredIndicators.length === 0 && (
                      <tr>
                        <td colSpan="4" className="empty-table">
                          No indicators match your search.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {!analysis && (
            <div className="empty-results">
              <div className="empty-results-icon">☷</div>

              <h4>Your analysis will appear here</h4>

              <p>
                Upload a PDF and run the analysis to explore all 40
                configured indicators and their supporting evidence.
              </p>
            </div>
          )}
        </section>

        {/* Footer */}
        <footer className="page-footer">
          <span>PrivAI · Privacy Compliance AI</span>

          <span>
            Phase 1 · Rule-based analysis · Human review required
          </span>
        </footer>
      </main>
    </div>
  )
}

export default App