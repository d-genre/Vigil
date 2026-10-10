import React from 'react'
import { Card } from '../components/ui/Card'
import { SectionHeading } from '../components/ui/SectionHeading'
import { StatusIndicator } from '../components/ui/StatusIndicator'

export const EvaluationView: React.FC = () => {
  return (
    <div className="view-container">
      <SectionHeading
        title="System Evaluation & Metrics"
        description="Model precision, recall, screening latency, and false positive metrics"
      />

      <Card
        title="Evaluation Benchmark Dashboard"
        action={<StatusIndicator label="Endpoint unmounted" variant="warning" />}
      >
        <div className="empty-module-state">
          <p className="empty-state-title">Benchmark Metrics Unavailable</p>
          <p className="empty-state-detail">
            Evaluation endpoint GET /evaluation is not currently mounted on the backend service. No operational metrics displayed.
          </p>
        </div>
      </Card>
    </div>
  )
}
