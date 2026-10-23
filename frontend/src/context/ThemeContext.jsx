import React, { createContext, useContext, useEffect, useState } from 'react'

const THEME_STORAGE_KEY = 'symbolon_theme'

const ThemeContext = createContext({
  theme: 'dark',
  resolvedTheme: 'dark',
  setTheme: () => {},
  toggleTheme: () => {},
})

export function ThemeProvider({ children }) {
  // Theme can be 'light', 'dark', or 'system'
  const [theme, setThemeState] = useState(() => {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY)
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        return stored
      }
    } catch (e) {
      console.warn('Unable to read theme from localStorage:', e)
    }
    return 'dark' // Default to approved dark navy & purple
  })

  // Determine actual rendered theme ('light' or 'dark')
  const [resolvedTheme, setResolvedTheme] = useState(() => {
    if (theme === 'system') {
      return typeof window !== 'undefined' &&
        window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
    }
    return theme
  })

  // Synchronize data-theme on <html> element and handle system preference changes
  useEffect(() => {
    function calculateResolved(t) {
      if (t === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      }
      return t
    }

    const currentResolved = calculateResolved(theme)
    setResolvedTheme(currentResolved)
    document.documentElement.setAttribute('data-theme', currentResolved)

    // Also persist in localStorage
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme)
    } catch (e) {
      console.warn('Unable to persist theme to localStorage:', e)
    }

    // Media query listener if in 'system' mode
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = (e) => {
        const newResolved = e.matches ? 'dark' : 'light'
        setResolvedTheme(newResolved)
        document.documentElement.setAttribute('data-theme', newResolved)
      }

      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [theme])

  function setTheme(newTheme) {
    if (newTheme === 'light' || newTheme === 'dark' || newTheme === 'system') {
      setThemeState(newTheme)
    }
  }

  function toggleTheme() {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
