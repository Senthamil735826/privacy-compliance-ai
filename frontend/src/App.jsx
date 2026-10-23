import React, { useEffect, useState } from 'react'
import './App.css'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { OverviewView } from './views/OverviewView'
import { AnalyzePolicyView } from './views/AnalyzePolicyView'
import { IndicatorExplorerView } from './views/IndicatorExplorerView'
import { EvidenceExplorerView } from './views/EvidenceExplorerView'
import { AgentAnalysisView } from './views/AgentAnalysisView'
import { PolicyLibraryView } from './views/PolicyLibraryView'
import { PolicyCompareView } from './views/PolicyCompareView'
import { SettingsView } from './views/SettingsView'

const LOCAL_STORAGE_KEY = 'symbolon_policy_library_v1'

export default function App() {
  const [currentView, setCurrentView] = useState('overview')
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [apiOnline, setApiOnline] = useState(true)

  // Document & Analysis State
  const [file, setFile] = useState(null)
  const [activePolicyName, setActivePolicyName] = useState('')
  const [documentId, setDocumentId] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Library of previously analyzed policies
  const [library, setLibrary] = useState(() => {
    try {
      const stored = localStorage.getItem(LOCAL_STORAGE_KEY)
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  })

  // Deep-linking context between views
  const [selectedIndicatorForEvidence, setSelectedIndicatorForEvidence] = useState('B7')
  const [targetIndicatorForAgent, setTargetIndicatorForAgent] = useState(null)

  // Save library changes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(library))
    } catch (e) {
      console.error('Failed to save policy library to localStorage:', e)
    }
  }, [library])

  // Periodic lightweight health ping to /api/health
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch('/api/health')
        setApiOnline(res.ok)
      } catch {
        setApiOnline(false)
      }
    }
    checkHealth()
    const timer = setInterval(checkHealth, 30000)
    return () => clearInterval(timer)
  }, [])

  // File selection
  function handleSelectFile(selectedFile) {
    if (!selectedFile) return
    setError('')

    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a valid PDF file.')
      return
    }

    if (selectedFile.size === 0) {
      setError('The selected PDF is empty.')
      return
    }

    setFile(selectedFile)
    setActivePolicyName(selectedFile.name)
  }

  // Upload and execute compliance analysis
  async function handleAnalyze() {
    if (!file) {
      setError('Select a privacy policy PDF before starting analysis.')
      return
    }

    setLoading(true)
    setError('')

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
        throw new Error('The server returned an invalid response. Verify that the backend is running.')
      }

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'The backend was unable to process the PDF document.'
        )
      }

      if (data.status !== 'success' || !Array.isArray(data.indicators) || !data.compliance_summary) {
        throw new Error('The server returned an unexpected response format.')
      }

      const docId = data.document_id || data.document?.document_id || `doc_${Date.now()}`
      setAnalysis(data)
      setDocumentId(docId)

      // Add to policy library
      const newEntry = {
        id: docId,
        name: file.name,
        date: new Date().toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        }),
        matched: data.compliance_summary.matched,
        total: data.compliance_summary.total_indicators || 40,
        coverage: data.compliance_summary.coverage || '0%',
        analysis: data,
      }

      setLibrary((prev) => {
        const filtered = prev.filter((p) => p.name !== file.name)
        return [newEntry, ...filtered]
      })
    } catch (err) {
      setError(err.message || 'Unable to connect to the backend.')
    } finally {
      setLoading(false)
    }
  }

  // Reset current workspace
  function handleResetAnalysis() {
    setFile(null)
    setAnalysis(null)
    setDocumentId(null)
    setActivePolicyName('')
    setError('')
  }

  // Load a policy from library into active workspace
  function handleSelectPolicyFromLibrary(entry) {
    if (!entry) return
    setActivePolicyName(entry.name)
    setDocumentId(entry.id)
    setAnalysis(entry.analysis)
    setError('')
  }

  // Delete from library
  function handleDeletePolicyFromLibrary(id) {
    setLibrary((prev) => prev.filter((item) => item.id !== id))
    if (documentId === id) {
      handleResetAnalysis()
    }
  }

  const matchedCount = analysis?.compliance_summary?.matched || 0
  const totalCount = analysis?.compliance_summary?.total_indicators || 40

  return (
    <div className="symbolon-shell">
      {/* Fixed Left Sidebar */}
      <Sidebar
        currentView={currentView}
        onNavigate={setCurrentView}
        activeDocumentName={activePolicyName}
        matchedCount={matchedCount}
        totalCount={totalCount}
        isOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="symbolon-main-wrapper">
        <Topbar
          currentView={currentView}
          onNavigate={setCurrentView}
          onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
          apiOnline={apiOnline}
        />

        <main className="symbolon-content" id="main-content">
          {currentView === 'overview' && (
            <OverviewView
              analysis={analysis}
              activeDocumentName={activePolicyName}
              onNavigate={setCurrentView}
            />
          )}

          {currentView === 'analyze' && (
            <AnalyzePolicyView
              file={file}
              onSelectFile={handleSelectFile}
              onAnalyze={handleAnalyze}
              loading={loading}
              error={error}
              analysis={analysis}
              onNavigate={setCurrentView}
              onReset={handleResetAnalysis}
            />
          )}

          {currentView === 'indicators' && (
            <IndicatorExplorerView
              analysis={analysis}
              onNavigate={setCurrentView}
              onSelectIndicatorForEvidence={(id) => setSelectedIndicatorForEvidence(id)}
              onSelectIndicatorForAgent={(ind) => setTargetIndicatorForAgent(ind)}
            />
          )}

          {currentView === 'evidence' && (
            <EvidenceExplorerView
              analysis={analysis}
              documentId={documentId}
              activePolicyName={activePolicyName}
              policies={library}
              onSelectPolicy={handleSelectPolicyFromLibrary}
              selectedIndicatorId={selectedIndicatorForEvidence}
              onNavigate={setCurrentView}
              onSelectIndicatorForAgent={(ind) => setTargetIndicatorForAgent(ind)}
            />
          )}

          {currentView === 'agents' && (
            <AgentAnalysisView
              targetIndicator={targetIndicatorForAgent}
              analysis={analysis}
            />
          )}

          {currentView === 'library' && (
            <PolicyLibraryView
              library={library}
              activeDocumentId={documentId}
              onSelectPolicy={handleSelectPolicyFromLibrary}
              onDeletePolicy={handleDeletePolicyFromLibrary}
              onNavigate={setCurrentView}
            />
          )}

          {currentView === 'compare' && (
            <PolicyCompareView
              library={library}
              onNavigate={setCurrentView}
            />
          )}

          {currentView === 'settings' && (
            <SettingsView apiOnline={apiOnline} />
          )}
        </main>
      </div>
    </div>
  )
}