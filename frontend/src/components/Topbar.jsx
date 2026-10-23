import React, { useState } from 'react'
import { Menu, Search, Bell, ChevronDown } from 'lucide-react'
import { BrandLogo } from './BrandLogo'
import { ThemeToggle } from './ThemeToggle'

export function Topbar({
  onNavigate,
  onToggleMobileSidebar,
  globalSearchQuery = '',
  onGlobalSearchChange,
}) {
  const [localQuery, setLocalQuery] = useState(globalSearchQuery)

  function handleSearch(e) {
    const val = e.target.value
    setLocalQuery(val)
    if (onGlobalSearchChange) {
      onGlobalSearchChange(val)
    }
  }

  return (
    <header className="symbolon-topbar">
      <div className="topbar-left">
        {/* Mobile menu trigger */}
        <button
          type="button"
          className="topbar-mobile-trigger"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle navigation drawer"
          title="Open menu"
        >
          <Menu size={20} />
        </button>

        {/* Mobile brand symbol + wordmark */}
        <div className="topbar-mobile-brand">
          <BrandLogo compact onClick={() => onNavigate('overview')} />
        </div>

        {/* Global Search Input (max ~620px) */}
        <div className="topbar-search-wrapper">
          <Search size={15} className="topbar-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="topbar-search-input"
            placeholder="Search policies, indicators, evidence..."
            value={localQuery}
            onChange={handleSearch}
            aria-label="Global search across policies and indicators"
          />
        </div>
      </div>

      <div className="topbar-right">
        {/* Theme Toggle Pill */}
        <div className="topbar-theme-toggle-wrap">
          <ThemeToggle />
        </div>

        {/* Notification Bell with red dot */}
        <button
          type="button"
          className="topbar-icon-btn topbar-bell-btn"
          aria-label="Notifications (1 unread alert)"
          title="Notifications"
        >
          <Bell size={18} />
          <span className="topbar-bell-dot" aria-hidden="true" />
        </button>

        {/* User Avatar Circle "JD" with chevron */}
        <div
          className="topbar-user-profile"
          role="button"
          tabIndex={0}
          aria-label="User account: Jane Doe"
        >
          <div className="topbar-avatar" aria-hidden="true">
            <span>JD</span>
          </div>
          <ChevronDown size={14} className="topbar-user-chevron" aria-hidden="true" />
        </div>
      </div>
    </header>
  )
}
