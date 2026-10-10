import React from 'react'

interface CardProps {
  title?: string
  subtitle?: string
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  className = '',
  action,
}) => {
  return (
    <div className={`ui-card ${className}`}>
      {(title || subtitle || action) && (
        <div className="ui-card-header">
          <div>
            {title && <h3 className="ui-card-title">{title}</h3>}
            {subtitle && <p className="ui-card-subtitle">{subtitle}</p>}
          </div>
          {action && <div className="ui-card-action">{action}</div>}
        </div>
      )}
      <div className="ui-card-body">{children}</div>
    </div>
  )
}
