import React from 'react'

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'default',
  badge,
}) {
  return (
    <div className={`metric-card metric-card--${variant}`}>
      <div className="metric-card-header">
        <span className="metric-card-title">{title}</span>
        {Icon && (
          <div className="metric-card-icon" aria-hidden="true">
            <Icon size={18} />
          </div>
        )}
      </div>

      <div className="metric-card-body">
        <div className="metric-card-value">{value}</div>
        {badge && <span className="metric-card-badge">{badge}</span>}
      </div>

      {subtitle && <div className="metric-card-subtitle">{subtitle}</div>}
    </div>
  )
}
