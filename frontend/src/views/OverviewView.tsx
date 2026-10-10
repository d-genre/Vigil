import React, { useEffect, useState } from 'react'
import { Card } from '../components/ui/Card'
import { SectionHeading } from '../components/ui/SectionHeading'
import { StatusIndicator } from '../components/ui/StatusIndicator'
import { apiService } from '../services/api'
import type { HealthResponse, Transaction } from '../types/api'
import type { NavItemId } from '../types/navigation'

interface OverviewViewProps {
  healthState?: {
    health: HealthResponse | null
    loading: boolean
    error: string | null
  }
  onRefreshHealth?: () => void
  onNavigate?: (id: NavItemId) => void
  onSelectTransactionForGraph?: (txId: string) => void
  onSelectTransactionForDossier?: (txId: string) => void
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  healthState,
  onRefreshHealth,
  onNavigate,
  onSelectTransactionForGraph,
}) => {
  const [internalHealth, setInternalHealth] = useState<HealthResponse | null>(null)
  const [internalLoading, setInternalLoading] = useState<boolean>(!healthState)
  const [internalError, setInternalError] = useState<string | null>(null)

  // Stream activity buffer state
  const [recentTxList, setRecentTxList] = useState<Transaction[]>([])
  const [streamLoading, setStreamLoading] = useState<boolean>(true)
  const [streamError, setStreamError] = useState<string | null>(null)

  const fetchHealthLocal = async () => {
    setInternalLoading(true)
    setInternalError(null)
    try {
      const data = await apiService.getHealth()
      setInternalHealth(data)
    } catch (err) {
      setInternalError(err instanceof Error ? err.message : 'Failed to connect to backend server')
    } finally {
      setInternalLoading(false)
    }
  }

  const fetchRecentStream = async () => {
    setStreamLoading(true)
    setStreamError(null)
    try {
      const data = await apiService.getStream(false)
      setRecentTxList(data.transactions ? data.transactions.slice(0, 5) : [])
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : 'Stream unavailable')
    } finally {
      setStreamLoading(false)
    }
  }

  useEffect(() => {
    if (!healthState) {
      fetchHealthLocal()
    }
    fetchRecentStream()
    const interval = setInterval(() => {
      fetchRecentStream()
    }, 3000)
    return () => clearInterval(interval)
  }, [healthState])

  const health = healthState ? healthState.health : internalHealth
  const loading = healthState ? healthState.loading : internalLoading
  const error = healthState ? healthState.error : internalError

  const handleRefresh = () => {
    if (onRefreshHealth) {
      onRefreshHealth()
    } else {
      fetchHealthLocal()
    }
    fetchRecentStream()
  }

  return (
    <div className="view-container">
      {/* 1. Header & Functional Refresh Action */}
      <SectionHeading
        title="System Overview"
        description="Autonomous Fraud Investigation Command Center"
        action={
          <button type="button" className="btn-secondary" onClick={handleRefresh} disabled={loading}>
            {loading ? 'Checking...' : 'Refresh Health'}
          </button>
        }
      />

      {error && (
        <div className="alert-card alert-error">
          <p className="alert-title">Backend Connection Failure</p>
          <p className="alert-detail">{error}</p>
        </div>
      )}

      {/* Top Split: Backend Health + Shortcuts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
        {/* Backend Health Card */}
        <Card
          title="1. Backend Health"
          action={
            <StatusIndicator
              label={loading && !health ? 'Checking API...' : health ? `Connected (${health.status.toUpperCase()})` : 'Backend Unavailable'}
              variant={loading && !health ? 'neutral' : health ? 'success' : 'error'}
            />
          }
        >
          <div className="tx-detail-grid">
            <div className="detail-item">
              <span className="detail-label">Gateway Connection:</span>
              <span className="detail-value font-bold">{loading && !health ? 'CHECKING...' : health ? 'CONNECTED' : 'UNAVAILABLE'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">API Version:</span>
              <span className="detail-value font-mono">{health ? `v${health.version}` : 'N/A'}</span>
            </div>
          </div>
        </Card>

        {/* Investigation Shortcuts Card */}
        <Card title="2. Investigation Shortcuts">
          <div className="btn-group-row" style={{ flexWrap: 'wrap', gap: '8px', paddingTop: '4px' }}>
            {onNavigate && (
              <>
                <button type="button" className="btn-secondary" onClick={() => onNavigate('investigations')}>
                  🔍 Live Investigations
                </button>
                <button type="button" className="btn-secondary" onClick={() => onNavigate('graph-explorer')}>
                  🕸️ Graph Explorer
                </button>
                <button type="button" className="btn-secondary" onClick={() => onNavigate('attack-lab')}>
                  ⚡ Attack Lab
                </button>
              </>
            )}
          </div>
        </Card>
      </div>

      {/* 3. Recent Transactions Stream Activity */}
      <Card
        title="3. Recent Transactions"
        subtitle="Live screened transactions from GET /api/transactions/stream"
        action={
          <div className="status-indicator-badge variant-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <span className="status-dot pulse-dot-anim" />
            <span className="status-label" style={{ fontWeight: 600 }}>Live Stream: 15s Cadence</span>
          </div>
        }
      >
        {streamError && (
          <div className="alert-card alert-error" style={{ marginBottom: '10px' }}>
            <p className="alert-title">Stream Unavailable</p>
            <p className="alert-detail">{streamError}</p>
          </div>
        )}

        {streamLoading && recentTxList.length === 0 && !streamError && (
          <div className="empty-module-state">
            <p className="empty-state-title">Loading Stream Transactions...</p>
            <p className="empty-state-detail">Querying recent transaction stream...</p>
          </div>
        )}

        {!streamLoading && recentTxList.length === 0 && !streamError && (
          <div className="empty-module-state">
            <p className="empty-state-title">No Recent Transactions</p>
            <p className="empty-state-detail">Stream buffer is empty. Run stream ticks in Investigations to populate buffer.</p>
          </div>
        )}

        {recentTxList.length > 0 && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Account ID</th>
                  <th>Amount</th>
                  <th>Risk Score</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentTxList.map((tx) => {
                  const txAny = tx as unknown as Record<string, unknown>
                  const accountId = tx.account_id || (txAny.user_id as string) || 'N/A'
                  const scoreVal = tx.risk_score ?? (txAny.catboost_score as number)
                  const statusStr = (txAny.status as string) || 'SCREENED'

                  return (
                    <tr key={tx.transaction_id}>
                      <td className="font-mono text-bold">{tx.transaction_id}</td>
                      <td className="font-mono">{accountId}</td>
                      <td>
                        {tx.amount?.toLocaleString('en-US', {
                          style: 'currency',
                          currency: tx.currency || 'USD',
                        })}
                      </td>
                      <td>
                        {scoreVal !== undefined ? (
                          <span className="font-mono text-bold">
                            {typeof scoreVal === 'number' ? scoreVal.toFixed(3) : scoreVal}
                          </span>
                        ) : (
                          <span className="text-muted">N/A</span>
                        )}
                      </td>
                      <td>
                        <span className="status-tag tag-ready">{statusStr}</span>
                      </td>
                      <td>
                        {onSelectTransactionForGraph && (
                          <button
                            type="button"
                            className="btn-primary"
                            onClick={() => onSelectTransactionForGraph(tx.transaction_id)}
                          >
                            Investigate Graph
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
