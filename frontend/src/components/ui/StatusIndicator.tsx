import React from 'react'

export type StatusVariant = 'neutral' | 'warning' | 'info' | 'error' | 'success'

interface StatusIndicatorProps {
  label: string
  variant?: StatusVariant
  className?: string
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  label,
  variant = 'neutral',
  className = '',
}) => {
  return (
    <div className={`status-indicator-badge variant-${variant} ${className}`}>
      <span className="status-dot" />
      <span className="status-label">{label}</span>
    </div>
  )
}
