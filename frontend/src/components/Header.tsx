import React from 'react'
import { StatusIndicator, type StatusVariant } from './ui/StatusIndicator'
import type { HealthResponse } from '../types/api'

interface HeaderProps {
  title: string
  health?: HealthResponse | null
  loading?: boolean
  error?: string | null
}

export const Header: React.FC<HeaderProps> = ({
  title,
  health,
  loading = false,
  error = null,
}) => {
  const getHeaderStatus = (): { label: string; variant: StatusVariant } => {
    if (loading && !health) {
      return { label: 'Checking Backend...', variant: 'neutral' }
    }
    if (error || !health) {
      return { label: 'Backend Offline', variant: 'error' }
    }
    return {
      label: `API v${health.version} (${health.status.toUpperCase()})`,
      variant: 'success',
    }
  }

  const { label, variant } = getHeaderStatus()

  return (
    <header className="workspace-header">
      <div className="header-left">
        <h1 className="header-page-title">{title}</h1>
      </div>
      <div className="header-right">
        <StatusIndicator label={label} variant={variant} />
      </div>
    </header>
  )
}
