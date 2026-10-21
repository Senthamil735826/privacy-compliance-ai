import { useMemo, useRef, useState } from 'react'
import './App.css'

const PRIMARY_INDICATORS = [
  {
    id: 'A1',
    name: 'Basic Information',
    secondaryIds: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6'],
  },
  {
    id: 'A2',
    name: 'Data Collection Rules',
    secondaryIds: ['B7', 'B8', 'B9', 'B10', 'B11', 'B12'],
  },
  {
    id: 'A3',
    name: 'Data Usage Rules',
    secondaryIds: ['B13', 'B14', 'B15'],
  },
  {
    id: 'A4',
    name: 'Data Storage and Security Measures',
    secondaryIds: ['B16', 'B17', 'B18', 'B19', 'B20', 'B21', 'B22'],
  },
  {
    id: 'A5',
    name: 'Personal Information and Subject Rights',
    secondaryIds: ['B23', 'B24', 'B25', 'B26', 'B27', 'B28', 'B29'],
  },
  {
    id: 'A6',
    name: 'Rules for Entrusted Processing, Sharing, Transfer, and Public Disclosure',
    secondaryIds: ['B30', 'B31', 'B32', 'B33', 'B34', 'B35'],
  },
  {
    id: 'A7',
    name: "Children's Privacy",
    secondaryIds: ['B36', 'B37', 'B38', 'B39', 'B40'],
  },
]

function App() {
  const fileInputRef = useRef(null)

  const [file, setFile] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [documentId, setDocumentId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [dragging, setDragging] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState({ A1: true })

  // Semantic search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [searchError, setSearchError] = useState('')

  const summary = analysis?.compliance_summary

  const indicators = useMemo(
    () => analysis?.indicators ?? [],
    [analysis],
  )

  const filteredIndicators = useMemo(() => {
    const query = search.trim().toLowerCase()

    return indicators.filter((indicator) => {
      const matchesFilter =
        filter === 'all' ||
        (filter === 'found' && indicator.matched) ||
        (filter === 'missing' && !indicator.matched)

      const matchesSearch =
        !query ||
        String(indicator.id ?? '').toLowerCase().includes(query) ||
        String(indicator.name ?? '').toLowerCase().includes(query) ||
        String(indicator.primary ?? '').toLowerCase().includes(query)

      return matchesFilter && matchesSearch
    })
  }, [indicators, filter, search])

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
    setDocumentId(null)
    setSearchResults(null)
    setSearchQuery('')
    setSearchError('')
    setExpandedGroups({ A1: true })
  }

  async function handleAnalyze() {
    if (!file) {
      setError('Select a privacy policy PDF before starting analysis.')
      return
    }

    setLoading(true)
    setError('')
    setAnalysis(null)
    setDocumentId(null)
    setSearchResults(null)
    setSearchError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/policy/upload', {
        method: 'POST',
        body: formData,
      })

      let data

      try {
        data = await response.json()
      } catch {
        throw new Error(
          'The server returned an invalid response. Check that the backend is running.',
        )
      }

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
      const docId = data.document_id || data.document?.document_id || null
      setDocumentId(docId)
      setFilter('all')
      setSearch('')
      setExpandedGroups({ A1: true })

      window.setTimeout(() => {
        document.getElementById('analysis-results')?.scrollIntoView({
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

  async function handleSemanticSearch(event) {
    if (event) event.preventDefault()

    const trimmedQuery = searchQuery.trim()
    if (!trimmedQuery) {
      setSearchError('Please enter a question or query.')
      return
    }

    if (!documentId) {
      setSearchError('Upload and analyze a policy first to enable semantic search.')
      return
    }

    setSearching(true)
    setSearchError('')

    try {
      const response = await fetch('/api/policy/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          query: trimmedQuery,
          top_k: 3,
        }),
      })

      let data

      try {
        data = await response.json()
      } catch {
        throw new Error('The server returned an invalid response.')
      }

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Failed to retrieve semantic search results.',
        )
      }

      setSearchResults(data.results || [])
    } catch (err) {
      setSearchError(err.message || 'Error occurred while executing semantic search.')
      setSearchResults(null)
    } finally {
      setSearching(false)
    }
  }

  function handleDrop(event) {
    event.preventDefault()
    setDragging(false)
    selectFile(event.dataTransfer.files?.[0])
  }

  function toggleGroup(groupId) {
    setExpandedGroups((previous) => ({
      ...previous,
      [groupId]: !previous[groupId],
    }))
  }

  const coverage = Number(summary?.coverage ?? 0)
  const matched = Number(summary?.matched ?? 0)
  const total = Number(summary?.total_indicators ?? indicators.length ?? 40)
  const notMatched = Number(summary?.not_matched ?? 0)

  return (
    <div className="app-shell">
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

          <a className="nav-link" href="#semantic-search">
            <span className="nav-icon">⌕</span>
            Semantic search
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

      <main className="main-content" id="overview">
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

            <div className="floating-chip chip-one">40 indicators</div>
            <div className="floating-chip chip-two">PDF analysis</div>
          </div>
        </section>

        <section className="metrics-grid" aria-label="Analysis summary">
          <article className="metric-card">
            <div className="metric-top">
              <span className="metric-icon purple">◉</span>
              <span className="metric-caption">OVERALL COVERAGE</span>
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
                  width: `${Math.min(100, Math.max(0, coverage))}%`,
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
              <span className="metric-muted">Requires review</span>
            </div>
          </article>

          <article className="metric-card">
            <div className="metric-top">
              <span className="metric-icon blue">▤</span>
              <span className="metric-caption">DOCUMENT PAGES</span>
            </div>

            <div className="metric-value">
              {analysis ? analysis.document?.total_pages ?? '—' : '—'}
            </div>

            <div className="metric-bottom">
              <span className="metric-muted">
                {analysis
                  ? `${analysis.document?.total_chunks ?? 0} text chunks`
                  : 'No document processed'}
              </span>
            </div>
          </article>
        </section>

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
                if (event.key === 'Enter' || event.key === ' ') {
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
                  <span className="file-format">PDF DOCUMENTS ONLY</span>
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
                Your PDF is processed by the configured backend. Review
                your backend deployment and storage settings to understand
                where uploaded documents are processed.
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
                <div className="pipeline-icon purple-bg">PDF</div>

                <div className="pipeline-copy">
                  <strong>Document ingestion</strong>
                  <p>Upload and extract PDF text</p>
                </div>

                <span className="pipeline-check">✓</span>
              </div>

              <div className="pipeline-connector" />

              <div className="pipeline-step">
                <div className="pipeline-icon blue-bg">TXT</div>

                <div className="pipeline-copy">
                  <strong>Text processing</strong>
                  <p>Clean and split the document</p>
                </div>

                <span className="pipeline-check">✓</span>
              </div>

              <div className="pipeline-connector" />

              <div className="pipeline-step">
                <div className="pipeline-icon green-bg">40</div>

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
                Keyword-based rules with evidence extraction. Results
                require human review and do not establish legal compliance.
              </p>
            </div>
          </article>
        </section>

        <section className="search-section" id="semantic-search">
          <div className="results-heading">
            <div>
              <span className="section-kicker">STEP 02</span>
              <h3>Semantic policy search</h3>
              <p>
                Ask questions in natural language to retrieve relevant policy passages with similarity scores.
              </p>
            </div>

            <div className="results-tag">
              <span className="results-tag-dot" />
              {documentId ? 'Document indexed' : 'Awaiting document'}
            </div>
          </div>

          <form className="search-form" onSubmit={handleSemanticSearch}>
            <div className="search-input-wrap">
              <span className="search-icon">⌕</span>
              <input
                type="text"
                placeholder={
                  documentId
                    ? "Ask a question (e.g. How long is personal data retained?)..."
                    : "Upload and analyze a policy above to enable semantic search..."
                }
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                disabled={!documentId || searching}
                aria-label="Semantic search query"
              />
            </div>

            <button
              type="submit"
              className="search-button"
              disabled={!documentId || searching || !searchQuery.trim()}
            >
              {searching ? (
                <>
                  <span className="spinner" />
                  Searching...
                </>
              ) : (
                <>
                  Search
                  <span className="button-arrow">→</span>
                </>
              )}
            </button>
          </form>

          {searchError && (
            <div className="error-message" role="alert">
              <span>!</span>
              {searchError}
            </div>
          )}

          {searchResults && (
            <div className="passages-grid">
              {searchResults.length > 0 ? (
                searchResults.map((result, index) => (
                  <article className="passage-card" key={`passage-${result.chunk_id}-${index}`}>
                    <div className="passage-header">
                      <div className="passage-header-left">
                        <span className="rank-badge">Rank #{index + 1}</span>
                        <span className="similarity-badge">
                          Score: {typeof result.similarity === 'number' ? result.similarity.toFixed(4) : result.similarity}
                        </span>
                      </div>
                      <span className="chunk-meta">
                        Chunk #{result.chunk_id} · Offsets: {result.start}–{result.end}
                      </span>
                    </div>
                    <p className="passage-text">&ldquo;{result.text}&rdquo;</p>
                  </article>
                ))
              ) : (
                <div className="search-empty-hint">
                  No relevant policy passages found matching your query.
                </div>
              )}
            </div>
          )}

          {!searchResults && !searchError && (
            <div className="search-empty-hint">
              {documentId
                ? "Enter a natural-language query above and click Search to retrieve evidence passages."
                : "Upload and analyze a PDF above to index its contents for semantic search."}
            </div>
          )}
        </section>

        <section className="results-section" id="analysis-results">
          <div className="results-heading">
            <div>
              <span className="section-kicker">STEP 03</span>
              <h3>Indicator analysis</h3>

              <p>
                {analysis
                  ? `${filteredIndicators.length} of ${indicators.length} indicators displayed`
                  : 'Upload and analyze a policy to see the results.'}
              </p>
            </div>

            <div className="results-tag">
              <span className="results-tag-dot" />
              {analysis ? 'Analysis complete' : 'Awaiting document'}
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
                    onChange={(event) => setSearch(event.target.value)}
                    aria-label="Search indicators"
                  />
                </div>

                <div className="filter-buttons">
                  <button
                    className={filter === 'all' ? 'selected' : ''}
                    onClick={() => setFilter('all')}
                  >
                    All ({indicators.length})
                  </button>

                  <button
                    className={filter === 'found' ? 'selected' : ''}
                    onClick={() => setFilter('found')}
                  >
                    Detected ({matched})
                  </button>

                  <button
                    className={filter === 'missing' ? 'selected' : ''}
                    onClick={() => setFilter('missing')}
                  >
                    Not detected ({notMatched})
                  </button>
                </div>
              </div>

              <div className="indicator-groups">
                {PRIMARY_INDICATORS.map((primary) => {
                  const groupIndicators = filteredIndicators.filter(
                    (indicator) =>
                      indicator.primary === primary.id &&
                      primary.secondaryIds.includes(indicator.id),
                  )

                  const totalInGroup = indicators.filter(
                    (indicator) =>
                      indicator.primary === primary.id &&
                      primary.secondaryIds.includes(indicator.id),
                  )

                  const detectedCount = totalInGroup.filter(
                    (indicator) => indicator.matched,
                  ).length

                  const isExpanded = Boolean(expandedGroups[primary.id])

                  return (
                    <section
                      className="indicator-group"
                      key={primary.id}
                    >
                      <button
                        type="button"
                        className="indicator-group-header"
                        onClick={() => toggleGroup(primary.id)}
                        aria-expanded={isExpanded}
                      >
                        <span className="group-chevron">
                          {isExpanded ? '▼' : '▶'}
                        </span>

                        <span className="group-title">
                          <strong>
                            {primary.id} — {primary.name}
                          </strong>

                          <small>
                            {detectedCount}/{totalInGroup.length} detected
                          </small>
                        </span>

                        <span className="group-progress">
                          {totalInGroup.length
                            ? Math.round(
                                (detectedCount / totalInGroup.length) * 100,
                              )
                            : 0}
                          %
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="indicator-table-wrap">
                          <table className="indicator-table">
                            <thead>
                              <tr>
                                <th>INDICATOR</th>
                                <th>STATUS</th>
                                <th>EVIDENCE</th>
                              </tr>
                            </thead>

                            <tbody>
                              {groupIndicators.map((indicator) => (
                                <tr key={indicator.id}>
                                  <td>
                                    <div className="indicator-name-cell">
                                      <span className="indicator-id">
                                        {indicator.id}
                                      </span>

                                      <div>
                                        <strong>{indicator.name}</strong>
                                        <small>{primary.id}</small>
                                      </div>
                                    </div>
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
                                                    {item.matched_by ||
                                                      'MATCH'}
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
                                                      (keyword, keywordIndex) => (
                                                        <span
                                                          key={`${keyword}-${keywordIndex}`}
                                                        >
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

                              {groupIndicators.length === 0 && (
                                <tr>
                                  <td
                                    colSpan="3"
                                    className="empty-table"
                                  >
                                    No indicators match the current
                                    search or filter.
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </section>
                  )
                })}
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