import React from 'react'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

  return (
    <div
      className="theme-toggle-pill"
      role="radiogroup"
      aria-label="Theme mode toggle"
    >
      <button
        type="button"
        className={`theme-toggle-btn ${!isDark ? 'theme-toggle-btn--active' : ''}`}
        onClick={() => setTheme('light')}
        role="radio"
        aria-checked={!isDark}
        aria-label="Switch to light mode"
        title="Light Mode"
      >
        <Sun size={15} />
      </button>

      <button
        type="button"
        className={`theme-toggle-btn ${isDark ? 'theme-toggle-btn--active' : ''}`}
        onClick={() => setTheme('dark')}
        role="radio"
        aria-checked={isDark}
        aria-label="Switch to dark mode"
        title="Dark Mode"
      >
        <Moon size={15} />
      </button>
    </div>
  )
}
