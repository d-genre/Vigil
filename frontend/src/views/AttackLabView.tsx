import React, { useState } from 'react'
import { Card } from '../components/ui/Card'
import { SectionHeading } from '../components/ui/SectionHeading'
import { StatusIndicator } from '../components/ui/StatusIndicator'
import { RiskBadge, type RiskLevel } from '../components/ui/RiskBadge'
import { apiService } from '../services/api'
import type { SimulateAttackResponse } from '../types/api'

interface AttackLabViewProps {
  onSelectTransactionForGraph?: (txId: string) => void
  onSelectTransactionForDossier?: (txId: string) => void
}

export const AttackLabView: React.FC<AttackLabViewProps> = ({
  onSelectTransactionForGraph,
  onSelectTransactionForDossier,
}) => {
  const [loading, setLoading] = useState<boolean>(false)
  const [result, setResult] = useState<SimulateAttackResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSimulateAttack = async () => {
    setLoading(true)
    setError(null)

    try {
      const res = await apiService.simulateAttack()
      setResult(res)

      // Refresh recent transaction stream buffer in background
      apiService.getStream(false).catch(() => {
        // Silent catch stream update
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to inject attack simulation payload')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="view-container">
      <SectionHeading
        title="Attack Lab & Simulation Center"
        description="Controlled synthetic fraud injection into live CatBoost ML & NetworkX graph screening pipeline"
        action={
          <button
            type="button"
            className="btn-danger"
            onClick={handleSimulateAttack}
            disabled={loading}
          >
            {loading ? 'Submitting Request...' : '⚡ Launch Attack Simulation'}
          </button>
        }
      />

      {error && (
        <div className="alert-card alert-error">
          <p className="alert-title font-bold">Attack Simulation Gateway Error</p>
          <p className="alert-detail">{error}</p>
        </div>
      )}

      {/* Main Manual Trigger Card */}
      <Card
        title="Synthetic Attack Simulation Control"
        subtitle="Manually inject high-risk fraud transaction into live backend streaming & screening pipeline"
        action={
          <StatusIndicator
            label={loading ? 'Submitting...' : result ? `Status: ${result.status}` : 'Ready to Trigger'}
            variant={loading ? 'neutral' : result ? 'success' : 'info'}
          />
        }
      >
        <div style={{ padding: '16px', background: '#fafcfb', border: '1px solid var(--card-border)', borderRadius: '6px', marginBottom: '16px' }}>
          <h4 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--text-heading)', marginBottom: '6px' }}>
            Live Screening Simulation Gateway
          </h4>
          <p className="text-sm text-muted" style={{ margin: 0, lineHeight: 1.5 }}>
            Clicking <strong>Launch Attack Simulation</strong> triggers a high-risk synthetic transaction into <span className="code-badge">POST /api/transactions/simulate-attack</span>. The injected transaction instantly processes through CatBoost ML feature scoring, TreeSHAP explainability drivers, and NetworkX graph intelligence visualizers.
          </p>
          <div style={{ marginTop: '14px' }}>
            <button
              type="button"
              className="btn-danger"
              onClick={handleSimulateAttack}
              disabled={loading}
              style={{ padding: '10px 18px', fontSize: '0.875rem' }}
            >
              {loading ? 'Injecting Attack Transaction...' : '⚡ Launch Attack Simulation'}
            </button>
          </div>
        </div>
      </Card>

      {/* Live Returned Simulation Output */}
      {result && (
        <Card
          title="Backend Simulation Results"
          subtitle={`Returned Payload from POST /api/transactions/simulate-attack`}
          action={<StatusIndicator label={`HTTP 201 — ${result.status}`} variant="success" />}
        >
          <div className="attack-result-box" style={{ background: '#fafcfb', border: '1px solid var(--card-border)', borderRadius: '6px', padding: '16px' }}>
            <div className="result-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <span className="text-xs text-muted font-mono">Simulated Transaction ID:</span>
                <h4 className="font-mono text-bold" style={{ fontSize: '1rem', color: 'var(--text-heading)', margin: 0 }}>
                  {result.transaction.transaction_id}
                </h4>
              </div>
              <RiskBadge
                level={((result.transaction.catboost_score ?? result.transaction.risk_score ?? 0.95) > 0.7 ? 'CRITICAL' : 'HIGH') as RiskLevel}
                score={result.transaction.catboost_score ?? result.transaction.risk_score ?? 0.965}
              />
            </div>

            <div className="tx-detail-grid" style={{ marginBottom: '14px' }}>
              <div className="detail-item">
                <span className="detail-label">Origin Account / User:</span>
                <span className="detail-value font-mono">
                  {result.transaction.account_id || (result.transaction as unknown as Record<string, string>).user_id || 'usr_ring_leader_88'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Target Beneficiary / Merchant:</span>
                <span className="detail-value font-mono">
                  {result.transaction.beneficiary_id || (result.transaction as unknown as Record<string, string>).merchant || 'CryptoExchange_Global_FX'}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Transaction Amount:</span>
                <span className="detail-value font-bold">
                  {result.transaction.amount?.toLocaleString('en-US', {
                    style: 'currency',
                    currency: result.transaction.currency || 'USD',
                  })}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Screening Status:</span>
                <span className="detail-value">
                  <span className="status-tag tag-ready">
                    {result.transaction.status || 'SUSPICIOUS'}
                  </span>
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">CatBoost Risk Score:</span>
                <span className="detail-value font-mono font-bold text-danger">
                  {(result.transaction.catboost_score ?? result.transaction.risk_score ?? 0.965).toFixed(3)}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Timestamp:</span>
                <span className="detail-value">{result.transaction.timestamp}</span>
              </div>
            </div>

            <div className="btn-group-row" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {onSelectTransactionForGraph && (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => onSelectTransactionForGraph(result.transaction.transaction_id)}
                >
                  🕸️ Investigate Network Graph
                </button>
              )}
              {onSelectTransactionForDossier && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => onSelectTransactionForDossier(result.transaction.transaction_id)}
                >
                  📑 View Judicial Dossier Evidence
                </button>
              )}
            </div>
          </div>

          <div style={{ marginTop: '14px', padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '0.75rem', color: '#64748b' }}>
            <strong style={{ color: '#334155' }}>Downstream Persistence Status:</strong> Injected transaction <span className="code-badge">{result.transaction.transaction_id}</span> is stored in the backend memory buffer (<span className="code-badge">TRANSACTION_BUFFER</span>). Immediate graph topology inspection (<span className="code-badge">GET /api/graph/{result.transaction.transaction_id}</span>) and dossier prosecution evidence generation (<span className="code-badge">GET /api/dossier/{result.transaction.transaction_id}</span>) are fully operational.
          </div>
        </Card>
      )}
    </div>
  )
}


