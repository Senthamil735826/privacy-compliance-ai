import { CheckCircle2, XCircle, AlertCircle, Clock } from 'lucide-react'

export function StatusBadge({ status, label, size = 'medium', showIcon = true }) {
  const norm = String(status ?? '').toLowerCase().trim()

  let typeClass = 'status-badge--neutral'
  let Icon = null
  let defaultLabel = label

  if (norm === 'found' || norm === 'detected' || norm === 'compliant') {
    typeClass = 'status-badge--found'
    Icon = CheckCircle2
    defaultLabel = label || 'Found'
  } else if (norm === 'not_found' || norm === 'missing' || norm === 'non_compliant') {
    typeClass = 'status-badge--not-found'
    Icon = XCircle
    defaultLabel = label || 'Not Found'
  } else if (norm === 'inconclusive') {
    typeClass = 'status-badge--inconclusive'
    Icon = AlertCircle
    defaultLabel = label || 'Inconclusive'
  } else if (norm === 'pending' || norm === 'evaluating') {
    typeClass = 'status-badge--pending'
    Icon = Clock
    defaultLabel = label || 'Evaluating'
  } else {
    typeClass = 'status-badge--neutral'
    defaultLabel = label || norm
  }

  const iconSize = size === 'large' ? 15 : size === 'small' ? 12 : 13

  return (
    <span className={`status-badge ${typeClass} status-badge--${size}`}>
      {showIcon && Icon && <Icon size={iconSize} className="status-badge-icon" aria-hidden="true" />}
      <span className="status-badge-label">{defaultLabel}</span>
    </span>
  )
}
