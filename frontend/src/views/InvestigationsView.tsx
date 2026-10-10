import React, { useEffect, useState, useCallback } from 'react'
import { Card } from '../components/ui/Card'
import { SectionHeading } from '../components/ui/SectionHeading'
import { StatusIndicator, type StatusVariant } from '../components/ui/StatusIndicator'
import { RiskBadge, type RiskLevel } from '../components/ui/RiskBadge'
import { apiService } from '../services/api'
import { wsService, type WsStatus } from '../services/websocket'
import type { Transaction } from '../types/api'

interface InvestigationsViewProps {
  onSelectTransactionForGraph?: (txId: string) => void
  onSelectTransactionForDossier?: (txId: string) => void
}

export const InvestigationsView: React.FC<InvestigationsViewProps> = ({
  onSelectTransactionForGraph,
  onSelectTransactionForDossier,
}) => {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [wsStatus, setWsStatus] = useState<WsStatus>('DISCONNECTED')
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null)
  const [autoTick, setAutoTick] = useState<boolean>(true)

  // Fetch initial stream buffer from GET /api/transactions/stream
  const fetchStream = useCallback(async (shouldTick: boolean = false) => {
    try {
      const data = await apiService.getStream(shouldTick)
      setTransactions((prev) => {
        const incomingIds = new Set(data.transactions.map((t) => t.transaction_id))
        const extraLocal = prev.filter((t) => !incomingIds.has(t.transaction_id))
        return [...data.transactions, ...extraLocal]
      })
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch transaction stream')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStream(false)

    // Polling interval to auto-sync latest backend stream state every 3s
    const interval = setInterval(() => {
      if (autoTick) {
        fetchStream(false)
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [fetchStream, autoTick])

  // WebSocket subscription setup & cleanup
  useEffect(() => {
    wsService.connect()

    const unsubStatus = wsService.subscribeStatus((status) => {
      setWsStatus(status)
    })

    const unsubEvent = wsService.subscribe((event) => {
      if (event.event_type === 'TRANSACTION_SCREENED' && event.data) {
        setTransactions((prev) => {
          const exists = prev.some((t) => t.transaction_id === event.data.transaction_id)
          if (exists) return prev
          return [event.data, ...prev]
        })
      }
    })

    return () => {
      unsubStatus()
      unsubEvent()
    }
  }, [])

  const getWsStatusVariant = (status: WsStatus): StatusVariant => {
    switch (status) {
      case 'CONNECTED':
        return 'success'
      case 'CONNECTING':
        return 'info'
      case 'ERROR':
        return 'error'
      default:
        return 'neutral'
    }
  }

  return (
    <div className="view-container">
      <SectionHeading
        title="Live Investigations Stream"
        description="Real-time transaction stream buffer, CatBoost risk screening & investigation queue"
        action={
          <div className="header-action-group">
            <button
              type="button"
              className={`btn-toggle ${autoTick ? 'active' : ''}`}
              onClick={() => setAutoTick(!autoTick)}
            >
              {autoTick ? 'Pause Auto-Sync' : 'Resume Auto-Sync'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => fetchStream(true)}
              disabled={loading}
            >
              {loading ? 'Polling...' : '⚡ Manual Stream Tick'}
            </button>
          </div>
        }
      />

      {error && (
        <div className="alert-card alert-error">
          <p className="alert-title">Stream Synchronization Error</p>
          <p className="alert-detail">{error}</p>
        </div>
      )}

      <Card
        title="Live Stream Buffer"
        subtitle={`Showing ${transactions.length} active screened transactions`}
        action={
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="status-indicator-badge variant-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span className="status-dot pulse-dot-anim" />
              <span className="status-label" style={{ fontWeight: 600 }}>Live Stream: 15s Cadence</span>
            </div>
            <StatusIndicator
              label={`WS: ${wsStatus}`}
              variant={getWsStatusVariant(wsStatus)}
            />
          </div>
        }
      >
        {transactions.length === 0 && !loading ? (
          <div className="empty-module-state">
            <p className="empty-state-title">Transaction stream empty</p>
            <p className="empty-state-detail">
              No transactions currently in stream buffer. Click "Tick Stream" to simulate incoming transactions.
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
                  <th>Location</th>
                  <th>Device / IP</th>
                  <th>Risk Tier</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => {
                  const isSelected = selectedTx?.transaction_id === tx.transaction_id
                  const txAny = tx as unknown as Record<string, unknown>
                  const accountId = tx.account_id || (txAny.user_id as string) || 'N/A'
                  const locationStr = tx.location || (txAny.merchant as string) || 'N/A'
                  const rawRisk = tx.risk_level || (txAny.status as string) || 'LOW'
                  const riskLevel = rawRisk as RiskLevel
                  const scoreVal = tx.risk_score ?? (txAny.catboost_score as number)

                  return (
                    <tr
                      key={tx.transaction_id}
                      className={isSelected ? 'selected-row' : ''}
                      onClick={() => setSelectedTx(tx)}
                    >
                      <td className="font-mono text-bold">{tx.transaction_id}</td>
                      <td className="text-muted">{tx.timestamp}</td>
                      <td className="font-mono">{accountId}</td>
                      <td>
                        {tx.amount?.toLocaleString('en-US', {
                          style: 'currency',
                          currency: tx.currency || 'USD',
                        })}
                      </td>
                      <td>{locationStr}</td>
                      <td className="font-mono text-sm">{tx.device_id || tx.ip || 'N/A'}</td>
                      <td>
                        <RiskBadge level={riskLevel} score={scoreVal} />
                      </td>
                      <td>
                        <div className="btn-group-sm">
                          {onSelectTransactionForGraph && (
                            <button
                              type="button"
                              className="btn-link"
                              onClick={(e) => {
                                e.stopPropagation()
                                onSelectTransactionForGraph(tx.transaction_id)
                              }}
                            >
                              Graph
                            </button>
                          )}
                          {onSelectTransactionForDossier && (
                            <button
                              type="button"
                              className="btn-link"
                              onClick={(e) => {
                                e.stopPropagation()
                                onSelectTransactionForDossier(tx.transaction_id)
                              }}
                            >
                              Dossier
                            </button>
                          )}
                        </div>
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
        <Card title={`Transaction Context: ${selectedTx.transaction_id}`}>
          <div className="tx-detail-grid">
            <div className="detail-item">
              <span className="detail-label">Account ID:</span>
              <span className="detail-value font-mono">
                {selectedTx.account_id || ((selectedTx as unknown as Record<string, unknown>).user_id as string) || 'N/A'}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Beneficiary ID:</span>
              <span className="detail-value font-mono">{selectedTx.beneficiary_id || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Device Fingerprint:</span>
              <span className="detail-value font-mono">{selectedTx.device_id || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">IP Address:</span>
              <span className="detail-value font-mono">{selectedTx.ip || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Transaction Type:</span>
              <span className="detail-value">{selectedTx.transaction_type || 'TRANSFER'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">CatBoost Risk Score:</span>
              <span className="detail-value">
                <RiskBadge
                  level={((selectedTx.risk_level || (selectedTx as unknown as Record<string, unknown>).status || 'LOW') as RiskLevel)}
                  score={selectedTx.risk_score ?? ((selectedTx as unknown as Record<string, unknown>).catboost_score as number)}
                />
              </span>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
