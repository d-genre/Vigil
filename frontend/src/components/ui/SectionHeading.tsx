import React from 'react'

interface SectionHeadingProps {
  title: string
  description?: string
  action?: React.ReactNode
}

export const SectionHeading: React.FC<SectionHeadingProps> = ({
  title,
  description,
  action,
}) => {
  return (
    <div className="ui-section-heading">
      <div>
        <h2 className="section-title">{title}</h2>
        {description && <p className="section-description">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
