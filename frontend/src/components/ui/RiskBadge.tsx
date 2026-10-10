import React from 'react'

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNSCORED'

interface RiskBadgeProps {
  level: RiskLevel
  score?: number
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, score }) => {
  const levelClass = level.toLowerCase()
  return (
    <span className={`risk-badge risk-${levelClass}`}>
      {level}
      {score !== undefined ? ` (${(score * 100).toFixed(0)}%)` : ''}
    </span>
  )
}
