import React, { useEffect } from 'react'
import {
  LayoutDashboard,
  UploadCloud,
  BookOpen,
  GitCompare,
  ShieldCheck,
  Search,
  Sparkles,
  Settings,
  FileText,
  CheckCircle2,
  X,
} from 'lucide-react'
import { BrandLogo } from './BrandLogo'

const NAV_SECTIONS = [
  {
    heading: 'WORKSPACE',
    items: [
      { id: 'overview', label: 'Overview', icon: LayoutDashboard },
      { id: 'analyze', label: 'Analyze Policy', icon: UploadCloud },
      { id: 'library', label: 'Policy Library', icon: BookOpen },
      { id: 'compare', label: 'Policy Comparison', icon: GitCompare },
    ],
  },
  {
    heading: 'INTELLIGENCE',
    items: [
      { id: 'indicators', label: 'Indicator Explorer', icon: ShieldCheck },
      { id: 'evidence', label: 'Evidence Explorer', icon: Search },
      { id: 'agents', label: 'Agent Analysis', icon: Sparkles },
    ],
  },
  {
    heading: 'SYSTEM',
    items: [
      { id: 'settings', label: 'Settings', icon: Settings },
    ],
  },
]

export function Sidebar({
  currentView,
  onNavigate,
  activeDocumentName,
  matchedCount = 0,
  totalCount = 40,
  isOpen = false,
  onCloseMobile,
}) {
  // Close drawer on Escape key press
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && isOpen && onCloseMobile) {
        onCloseMobile()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onCloseMobile])

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`symbolon-sidebar ${isOpen ? 'symbolon-sidebar--mobile-open' : ''}`}
        aria-label="Sidebar Navigation"
      >
        {/* Brand Header with optional mobile close button */}
        <div className="sidebar-brand-container">
          <BrandLogo
            onClick={() => {
              onNavigate('overview')
              if (onCloseMobile) onCloseMobile()
            }}
          />

          {onCloseMobile && (
            <button
              type="button"
              className="sidebar-mobile-close-btn"
              onClick={onCloseMobile}
              aria-label="Close navigation drawer"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Navigation Groups */}
        <nav className="sidebar-nav" aria-label="Main Navigation">
          {NAV_SECTIONS.map((section) => (
            <div key={section.heading} className="sidebar-section">
              <div className="sidebar-section-heading">{section.heading}</div>
              <ul className="sidebar-menu">
                {section.items.map((item) => {
                  const Icon = item.icon
                  const isActive = currentView === item.id
                  return (
                    <li key={item.id} className="sidebar-menu-item">
                      <button
                        type="button"
                        className={`sidebar-link ${isActive ? 'sidebar-link--active' : ''}`}
                        onClick={() => {
                          onNavigate(item.id)
                          if (onCloseMobile) onCloseMobile()
                        }}
                      >
                        <Icon className="sidebar-link-icon" size={18} />
                        <span className="sidebar-link-text">{item.label}</span>
                        {isActive && <span className="sidebar-link-indicator" aria-hidden="true" />}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Bottom Promo Card & Version */}
        <div className="sidebar-footer">
          <div className="sidebar-promo-card">
            <div className="sidebar-promo-wave" aria-hidden="true">
              <svg viewBox="0 0 200 40" fill="none" preserveAspectRatio="none">
                <path
                  d="M0 25C40 10 70 35 110 20C150 5 180 30 200 15V40H0V25Z"
                  fill="url(#promo-wave-grad)"
                  opacity="0.25"
                />
                <defs>
                  <linearGradient id="promo-wave-grad" x1="0" y1="0" x2="200" y2="40" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#6D6AF0" />
                    <stop offset="1" stopColor="#C8A45A" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="sidebar-promo-content">
              <div className="sidebar-promo-badge">AI-Powered Privacy Intelligence</div>
              <p className="sidebar-promo-text">
                Understand policies. Identify compliance gaps. Explore evidence.
              </p>
            </div>
          </div>

          <div className="sidebar-version-tag">
            <span>Symbolon Law</span>
            <span className="sidebar-version-pill">v1.0</span>
          </div>
        </div>
      </aside>
    </>
  )
}
