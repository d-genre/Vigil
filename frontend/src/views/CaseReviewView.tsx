import React, { useEffect, useState } from 'react'
import { Card } from '../components/ui/Card'
import { SectionHeading } from '../components/ui/SectionHeading'
import { StatusIndicator } from '../components/ui/StatusIndicator'
import { RiskBadge, type RiskLevel } from '../components/ui/RiskBadge'
import { apiService } from '../services/api'
import type { Transaction } from '../types/api'

interface LocalDecision {
  action: 'APPROVE' | 'HOLD' | 'ESCALATE' | 'BLOCK'
  reason: string
  updatedAt: string
}

export const CaseReviewView: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null)
  const [localDecisions, setLocalDecisions] = useState<Record<string, LocalDecision>>({})

  // Form input state
  const [actionChoice, setActionChoice] = useState<'APPROVE' | 'HOLD' | 'ESCALATE' | 'BLOCK'>('HOLD')
  const [reasonInput, setReasonInput] = useState<string>('')

  const fetchDbHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiService.getDbTransactions(50, 0)
      setTransactions(data.transactions || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to query database transaction history')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDbHistory()
  }, [])

  const handleRecordLocalDecision = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedTx) return

    const newDecision: LocalDecision = {
      action: actionChoice,
      reason: reasonInput || 'Manual analyst review decision',
      updatedAt: new Date().toISOString(),
    }

    setLocalDecisions((prev) => ({
      ...prev,
      [selectedTx.transaction_id]: newDecision,
    }))

    setReasonInput('')
  }

  return (
    <div className="view-container">
      <SectionHeading
        title="Case Review Queue"
        description="Persisted SQLite database transaction history & analyst review console"
        action={
          <button type="button" className="btn-secondary" onClick={fetchDbHistory} disabled={loading}>
            {loading ? 'Querying DB...' : 'Refresh DB History'}
          </button>
        }
      />

      {error && (
        <div className="alert-card alert-error">
          <p className="alert-title">Database Query Error</p>
          <p className="alert-detail">{error}</p>
        </div>
      )}

      <Card
        title="Persisted Transactions Database (`GET /transactions`)"
        subtitle="SQLite DB query limit: 50 records"
        action={
          <StatusIndicator
            label="Decision API /cases Unmounted (Decisions strictly local)"
            variant="warning"
          />
        }
      >
        {transactions.length === 0 && !loading ? (
          <div className="empty-module-state">
            <p className="empty-state-title">No transactions recorded in database</p>
            <p className="empty-state-detail">
              SQLite database contains no records. Submit transactions via POST /transactions or run stream ticks to populate DB.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Timestamp</th>
                  <th>Account ID</th>
                  <th>Amount</th>
                  <th>Risk Tier</th>
                  <th>Analyst Decision (Local)</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => {
                  const decision = localDecisions[tx.transaction_id]
                  const isSelected = selectedTx?.transaction_id === tx.transaction_id
                  return (
                    <tr
                      key={tx.transaction_id}
                      className={isSelected ? 'selected-row' : ''}
                      onClick={() => setSelectedTx(tx)}
                    >
                      <td className="font-mono text-bold">{tx.transaction_id}</td>
                      <td className="text-muted">{tx.timestamp}</td>
                      <td className="font-mono">{tx.account_id}</td>
                      <td>
                        {tx.amount?.toLocaleString('en-US', {
                          style: 'currency',
                          currency: tx.currency || 'USD',
                        })}
                      </td>
                      <td>
                        <RiskBadge level={(tx.risk_level || 'LOW') as RiskLevel} score={tx.risk_score} />
                      </td>
                      <td>
                        {decision ? (
                          <span className={`decision-tag decision-${decision.action.toLowerCase()}`}>
                            {decision.action} (Local)
                          </span>
                        ) : (
                          <span className="text-muted text-sm">PENDING_REVIEW</span>
                        )}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedTx(tx)
                          }}
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selectedTx && (
        <Card title={`Case Review Console: ${selectedTx.transaction_id}`}>
          <div className="local-warning-banner">
            <span className="warning-label">Notice:</span>
            <span>
              The backend <span className="code-badge">/cases/{selectedTx.transaction_id}/decision</span> endpoint is currently unmounted. Recorded decisions below will be held in client memory only and will not persist to the server database.
            </span>
          </div>

          <form onSubmit={handleRecordLocalDecision} className="decision-form">
            <div className="form-group">
              <label className="form-label">Select Review Decision:</label>
              <div className="radio-group-row">
                {(['APPROVE', 'HOLD', 'ESCALATE', 'BLOCK'] as const).map((choice) => (
                  <label key={choice} className={`radio-pill choice-${choice.toLowerCase()} ${actionChoice === choice ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="actionChoice"
                      value={choice}
                      checked={actionChoice === choice}
                      onChange={() => setActionChoice(choice)}
                    />
                    {choice}
                  </label>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Auditor Trail Rationale:</label>
              <textarea
                className="form-textarea"
                rows={3}
                value={reasonInput}
                onChange={(e) => setReasonInput(e.target.value)}
                placeholder="Enter analyst rationale supporting decision..."
              />
            </div>

            <button type="submit" className="btn-primary">
              Record Decision (Local State)
            </button>
          </form>

          {localDecisions[selectedTx.transaction_id] && (
            <div className="recorded-decision-box">
              <h4>Recorded Client Decision (Non-Persistent)</h4>
              <p>Action: <strong>{localDecisions[selectedTx.transaction_id].action}</strong></p>
              <p>Rationale: {localDecisions[selectedTx.transaction_id].reason}</p>
              <p className="text-xs text-muted">Recorded at: {localDecisions[selectedTx.transaction_id].updatedAt}</p>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
