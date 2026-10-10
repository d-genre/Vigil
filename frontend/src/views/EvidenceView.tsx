import React, { useEffect, useState } from 'react'
import { Card } from '../components/ui/Card'
import { SectionHeading } from '../components/ui/SectionHeading'
import { RiskBadge, type RiskLevel } from '../components/ui/RiskBadge'
import { apiService } from '../services/api'
import type { DossierResponse } from '../types/api'

interface EvidenceViewProps {
  initialTransactionId?: string
}

export const EvidenceView: React.FC<EvidenceViewProps> = ({
  initialTransactionId = 'TX_FLAGGED_9823',
}) => {
  const [transactionId, setTransactionId] = useState<string>(initialTransactionId)
  const [inputTxId, setInputTxId] = useState<string>(initialTransactionId)
  const [dossier, setDossier] = useState<DossierResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Keep state synchronized with incoming initialTransactionId prop
  useEffect(() => {
    if (initialTransactionId) {
      setTransactionId(initialTransactionId)
      setInputTxId(initialTransactionId)
    }
  }, [initialTransactionId])

  // Fetch judicial dossier with cancellation & stale data clearing
  useEffect(() => {
    let isMounted = true

    if (!transactionId || !transactionId.trim()) {
      setDossier(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    setDossier(null) // Clear stale data immediately on request start

    apiService
      .getDossier(transactionId)
      .then((data) => {
        if (isMounted) {
          setDossier(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch judicial dossier')
          setDossier(null) // Clear stale data on request failure
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [transactionId])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputTxId.trim()) {
      setTransactionId(inputTxId.trim())
    }
  }

  const handlePdfDownload = () => {
    const pdfUrl = apiService.getDossierPdfUrl(transactionId)
    window.open(pdfUrl, '_blank')
  }

  return (
    <div className="view-container">
      <SectionHeading
        title="Evidence & Judicial Dossier"
        description="Prosecution risk indicators vs defense counter-evidence & SHAP explainability drivers"
        action={
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              className="form-input"
              value={inputTxId}
              onChange={(e) => setInputTxId(e.target.value)}
              placeholder="Enter Transaction ID..."
            />
            <button type="submit" className="btn-secondary" disabled={loading}>
              Fetch Dossier
            </button>
          </form>
        }
      />

      {error && (
        <div className="alert-card alert-error">
          <p className="alert-title">Dossier Retrieval Error</p>
          <p className="alert-detail">{error}</p>
        </div>
      )}

      {loading && !dossier && !error && (
        <div className="empty-module-state">
          <p className="empty-state-title">Loading Judicial Dossier...</p>
          <p className="empty-state-detail">Evaluating prosecution evidence and defense factors for transaction {transactionId}</p>
        </div>
      )}

      {dossier && (
        <>
          <Card
            title={`Judicial Dossier: ${dossier.transaction_id}`}
            subtitle={`Classification: ${dossier.classification.replace(/_/g, ' ')}`}
            action={
              <div className="btn-group-row">
                <RiskBadge
                  level={(dossier.risk_score > 0.7 ? 'CRITICAL' : dossier.risk_score > 0.4 ? 'MEDIUM' : 'LOW') as RiskLevel}
                  score={dossier.risk_score}
                />
                <button type="button" className="btn-primary" onClick={handlePdfDownload}>
                  📄 Download PDF Dossier
                </button>
              </div>
            }
          >
            <div className="verdict-banner">
              <span className="verdict-label">Judicial Verdict Recommendation:</span>
              <span className="verdict-tag">{dossier.verdict}</span>
            </div>

            <p className="executive-summary-text">{dossier.executive_summary}</p>
          </Card>

          <div className="evidence-grid-row">
            {/* Prosecution Evidence Column */}
            <Card
              title={`Prosecution Evidence (${dossier.prosecution_evidence.length})`}
              subtitle="Aggregated risk indicators supporting escalation/blocking"
              className="prosecution-card"
            >
              {dossier.prosecution_evidence.length === 0 ? (
                <p className="text-muted italic">No prosecution risk indicators detected for this transaction.</p>
              ) : (
                <div className="evidence-item-list">
                  {dossier.prosecution_evidence.map((ev, idx) => (
                    <div key={idx} className="evidence-box prosecution-box">
                      <div className="evidence-box-header">
                        <span className="evidence-title">{ev.title}</span>
                        {ev.impact !== undefined && (
                          <span className="impact-badge font-mono">+{ev.impact.toFixed(2)}</span>
                        )}
                      </div>
                      <p className="evidence-desc">{ev.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Defense Counter-Evidence Column */}
            <Card
              title={`Defense Counter-Evidence (${dossier.defense_evidence.length})`}
              subtitle="Mitigating factors supporting transaction legitimacy"
              className="defense-card"
            >
              {dossier.defense_evidence.length === 0 ? (
                <p className="text-muted italic">No defense counter-evidence detected for this transaction.</p>
              ) : (
                <div className="evidence-item-list">
                  {dossier.defense_evidence.map((ev, idx) => (
                    <div key={idx} className="evidence-box defense-box">
                      <div className="evidence-box-header">
                        <span className="evidence-title">{ev.title}</span>
                      </div>
                      <p className="evidence-desc">{ev.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* SHAP Feature Explainability Drivers */}
          <Card title="SHAP Model Feature Explainability Drivers">
            <div className="shap-drivers-grid">
              {dossier.explainability_drivers.map((driver, idx) => {
                const isPositive = driver.shap_value > 0
                return (
                  <div key={idx} className="shap-driver-row">
                    <span className="driver-feature font-mono">{driver.feature}</span>
                    <span className="driver-value">{driver.value}</span>
                    <span className={`driver-shap font-mono ${isPositive ? 'text-danger' : 'text-success'}`}>
                      {isPositive ? `+${driver.shap_value.toFixed(3)}` : driver.shap_value.toFixed(3)}
                    </span>
                  </div>
                )
              })}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
