import React, { useEffect, useState } from 'react'
import { Card } from '../components/ui/Card'
import { SectionHeading } from '../components/ui/SectionHeading'
import { StatusIndicator } from '../components/ui/StatusIndicator'
import { RiskBadge, type RiskLevel } from '../components/ui/RiskBadge'
import { apiService } from '../services/api'
import type {
  GraphResponse,
  EgoNetworkResponse,
  TemporalMapResponse,
  TemporalMapPoint,
} from '../types/api'

type ViewMode = 'ego-network' | 'temporal-map'

interface GraphExplorerViewProps {
  initialTransactionId?: string
}

export const GraphExplorerView: React.FC<GraphExplorerViewProps> = ({
  initialTransactionId = 'TX_FLAGGED_9823',
}) => {
  const [transactionId, setTransactionId] = useState<string>(initialTransactionId)
  const [inputTxId, setInputTxId] = useState<string>(initialTransactionId)
  const [viewMode, setViewMode] = useState<ViewMode>('ego-network')

  const [egoData, setEgoData] = useState<EgoNetworkResponse | null>(null)
  const [temporalData, setTemporalData] = useState<TemporalMapResponse | null>(null)
  const [graphData, setGraphData] = useState<GraphResponse | null>(null)

  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Keep state synchronized with incoming initialTransactionId prop
  useEffect(() => {
    if (initialTransactionId) {
      setTransactionId(initialTransactionId)
      setInputTxId(initialTransactionId)
    }
  }, [initialTransactionId])

  // Fetch graph data for current transaction ID across endpoints
  useEffect(() => {
    let isMounted = true

    if (!transactionId || !transactionId.trim()) {
      setEgoData(null)
      setTemporalData(null)
      setGraphData(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    setEgoData(null)
    setTemporalData(null)
    setGraphData(null)

    Promise.all([
      apiService.getEgoNetwork(transactionId).catch(() => null),
      apiService.getTemporalMap(transactionId).catch(() => null),
      apiService.getGraph(transactionId).catch(() => null),
    ]).then(([egoRes, tempRes, graphRes]) => {
      if (isMounted) {
        setEgoData(egoRes)
        setTemporalData(tempRes)
        setGraphData(graphRes)
        setLoading(false)
      }
    }).catch((err) => {
      if (isMounted) {
        setError(err instanceof Error ? err.message : 'Failed to fetch graph intelligence views')
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

  return (
    <div className="view-container">
      <SectionHeading
        title="Graph Explorer & Intelligence Radar"
        description="NetworkX Fraudster Ego Network (Degrees of Separation) & Global Temporal IP Velocity Map"
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
              Fetch Graph
            </button>
          </form>
        }
      />

      {error && (
        <div className="alert-card alert-error">
          <p className="alert-title">Graph Intelligence Retrieval Error</p>
          <p className="alert-detail">{error}</p>
        </div>
      )}

      {loading && !egoData && !graphData && (
        <div className="empty-module-state">
          <p className="empty-state-title">Loading Graph Intelligence...</p>
          <p className="empty-state-detail">Querying NetworkX multi-tier topology and geo-velocity map for transaction {transactionId}</p>
        </div>
      )}

      {(egoData || graphData) && (
        <>
          {/* Mode Selector - Only 2 Views: Ego Network & Temporal IP Fraud Map */}
          <div className="radio-group-row" style={{ marginBottom: '16px' }}>
            <button
              type="button"
              className={`radio-pill ${viewMode === 'ego-network' ? 'selected' : ''}`}
              onClick={() => setViewMode('ego-network')}
            >
              🕸️ Fraudster Ego Network (Degrees of Separation)
            </button>
            <button
              type="button"
              className={`radio-pill ${viewMode === 'temporal-map' ? 'selected' : ''}`}
              onClick={() => setViewMode('temporal-map')}
            >
              🗺️ Temporal IP Fraud Map
            </button>
          </div>

          {/* View 1: Fraudster Ego Network */}
          {viewMode === 'ego-network' && (
            <EgoNetworkVisualizer
              key={transactionId}
              data={egoData || (graphData as unknown as EgoNetworkResponse)}
              onSelectTransaction={(txId) => {
                setTransactionId(txId)
                setInputTxId(txId)
              }}
            />
          )}

          {/* View 2: Temporal IP Fraud Map */}
          {viewMode === 'temporal-map' && (
            <TemporalMapVisualizer
              key={transactionId}
              data={temporalData}
              transactionId={transactionId}
            />
          )}
        </>
      )}
    </div>
  )
}

// ============================================================================
// Component 1: Vigil: Fraudster Ego Network (Degrees of Separation)
// ============================================================================
interface EgoNetworkVisualizerProps {
  data: EgoNetworkResponse | null
  onSelectTransaction?: (txId: string) => void
}

const EgoNetworkVisualizer: React.FC<EgoNetworkVisualizerProps> = ({
  data,
  onSelectTransaction,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
  const [zoomScale, setZoomScale] = useState<number>(1.0)

  useEffect(() => {
    setSelectedNodeId(null)
  }, [data?.transaction_id])

  if (!data) return null

  const nodes = data.nodes || []
  const links = data.links || data.edges || []

  // Layout positions: Concentric circles based on layer (0=Center, 1=Inner Ring, 2=Outer Ring)
  const layer0 = nodes.filter((n) => n.layer === 0 || n.type === 'center')
  const layer1 = nodes.filter((n) => (n.layer === 1 || n.type === 'transaction' || n.type === 'event') && !layer0.includes(n))
  const layer2 = nodes.filter((n) => (n.layer === 2 || (!layer0.includes(n) && !layer1.includes(n))))

  const cx = 360
  const cy = 270

  const positions = new Map<string, { x: number; y: number; layer: number }>()

  // Place Layer 0 in center
  layer0.forEach((n) => positions.set(n.id, { x: cx, y: cy, layer: 0 }))

  // Place Layer 1 on Ring 1 (r = 135)
  const r1 = 135
  layer1.forEach((n, i) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(1, layer1.length)
    positions.set(n.id, {
      x: cx + r1 * Math.cos(angle),
      y: cy + r1 * Math.sin(angle),
      layer: 1,
    })
  })

  // Place Layer 2 on Ring 2 (r = 235)
  const r2 = 235
  layer2.forEach((n, i) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(1, layer2.length)
    positions.set(n.id, {
      x: cx + r2 * Math.cos(angle),
      y: cy + r2 * Math.sin(angle),
      layer: 2,
    })
  })

  // Fallback for unmapped nodes
  nodes.forEach((n, idx) => {
    if (!positions.has(n.id)) {
      const angle = (2 * Math.PI * idx) / nodes.length
      positions.set(n.id, { x: cx + 180 * Math.cos(angle), y: cy + 180 * Math.sin(angle), layer: 1 })
    }
  })

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || nodes.find((n) => n.id === data.transaction_id) || nodes[0]
  const connectedLinks = links.filter((l) => l.source === selectedNode?.id || l.target === selectedNode?.id)

  return (
    <Card
      title="Vigil: Fraudster Ego Network (Degrees of Separation)"
      subtitle={`Target Transaction: ${data.transaction_id} | Multi-Layer Entity Radial Ring Topology`}
      action={
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setZoomScale((z) => Math.min(z + 0.15, 1.5))}
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
          >
            ➕ Zoom In
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setZoomScale((z) => Math.max(z - 0.15, 0.7))}
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
          >
            ➖ Zoom Out
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setZoomScale(1.0)
              setSelectedNodeId(nodes[0]?.id || null)
            }}
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
          >
            🎯 Fit View
          </button>
          <StatusIndicator
            label={`${nodes.length} Network Nodes | ${links.length} Relations`}
            variant={data.topology_stats?.suspicious_subgraph_nodes > 0 ? 'error' : 'success'}
          />
        </div>
      }
    >
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '16px' }}>
        {/* SVG Visualization Canvas */}
        <div style={{ position: 'relative', background: '#fafcfb', border: '1px solid var(--card-border)', borderRadius: '8px', padding: '8px', overflow: 'hidden' }}>
          <svg width="100%" height="540" viewBox="0 0 720 540" style={{ display: 'block', margin: '0 auto' }}>
            <g transform={`scale(${zoomScale})`} transform-origin="360 270">
              {/* Concentric Layer Ring Circles */}
              <circle cx="360" cy="270" r="135" stroke="#cbd5e1" strokeDasharray="4 4" strokeWidth="1.5" fill="none" />
              <text x="360" y="125" textAnchor="middle" fill="#64748b" fontSize="10" fontWeight="700">
                RING 1: ATTACKS & TRANSACTIONS (LAYER 1)
              </text>

              <circle cx="360" cy="270" r="235" stroke="#e2e8f0" strokeDasharray="4 4" strokeWidth="1.5" fill="none" />
              <text x="360" y="25" textAnchor="middle" fill="#94a3b8" fontSize="9" fontWeight="700">
                RING 2: TARGET MERCHANTS & INFRASTRUCTURE (LAYER 2)
              </text>

              {/* Edge Lines */}
              {links.map((link, idx) => {
                const sPos = positions.get(link.source)
                const tPos = positions.get(link.target)
                if (!sPos || !tPos) return null

                const isConnected = selectedNodeId && (link.source === selectedNodeId || link.target === selectedNodeId)
                const isHovered = hoveredNodeId && (link.source === hoveredNodeId || link.target === hoveredNodeId)

                const strokeColor = isConnected || isHovered ? '#dc2626' : '#cbd5e1'
                const strokeWidth = isConnected || isHovered ? 2.5 : 1.2

                const midX = (sPos.x + tPos.x) / 2
                const midY = (sPos.y + tPos.y) / 2

                return (
                  <g key={`${link.source}-${link.target}-${idx}`}>
                    <line
                      x1={sPos.x}
                      y1={sPos.y}
                      x2={tPos.x}
                      y2={tPos.y}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeOpacity={isConnected || isHovered ? 1.0 : 0.65}
                    />
                    {(isConnected || isHovered) && (
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect x="-40" y="-9" width="80" height="18" rx="4" fill="#ffffff" stroke={strokeColor} strokeWidth="1" />
                        <text x="0" y="3" textAnchor="middle" fill="#0f172a" fontSize="8" fontWeight="700">
                          {link.relation}
                        </text>
                      </g>
                    )}
                  </g>
                )
              })}

              {/* Network Nodes */}
              {nodes.map((node) => {
                const pos = positions.get(node.id)
                if (!pos) return null

                const isCenter = pos.layer === 0
                const isSelected = selectedNodeId === node.id
                const isHovered = hoveredNodeId === node.id

                const r = isCenter ? 26 : pos.layer === 1 ? 20 : 16
                const fill = node.color || (isCenter ? '#111111' : pos.layer === 1 ? '#2ca02c' : '#1f77b4')

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedNodeId(node.id)}
                    onMouseEnter={() => setHoveredNodeId(node.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                  >
                    {(isSelected || isCenter) && (
                      <circle
                        r={r + 6}
                        fill="none"
                        stroke={isSelected ? '#f59e0b' : '#ef4444'}
                        strokeWidth="2.5"
                        strokeDasharray={isSelected ? 'none' : '3 3'}
                      />
                    )}

                    <circle
                      r={r}
                      fill={fill}
                      stroke={isSelected ? '#f59e0b' : isHovered ? '#38bdf8' : '#ffffff'}
                      strokeWidth={isSelected ? 3 : 2}
                    />

                    <text x="0" y="4" textAnchor="middle" fontSize={isCenter ? '13' : '10'} fill="#ffffff" fontWeight="700">
                      {isCenter ? '👑' : pos.layer === 1 ? '⚡' : node.type === 'ip' ? '🌐' : node.type === 'device' ? '💻' : '🏪'}
                    </text>

                    <text
                      x="0"
                      y={r + 14}
                      textAnchor="middle"
                      fill={isSelected ? '#0f172a' : '#475569'}
                      fontSize={isSelected ? '11' : '10'}
                      fontWeight={isSelected || isCenter ? '700' : '500'}
                    >
                      {node.label.length > 20 ? `${node.label.substring(0, 18)}...` : node.label}
                    </text>
                  </g>
                )
              })}
            </g>
          </svg>

          {/* Legend Overlay */}
          <div
            style={{
              position: 'absolute',
              bottom: '12px',
              left: '12px',
              background: 'rgba(255, 255, 255, 0.94)',
              border: '1px solid var(--card-border)',
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '0.75rem',
              backdropFilter: 'blur(4px)',
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: '4px', color: '#1e293b' }}>Ego Network Layer Palette</div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <span style={{ color: '#111111', fontWeight: 700 }}>● Core Fraudster (Layer 0)</span>
              <span style={{ color: '#2ca02c', fontWeight: 700 }}>● Intermediate Attacks (Layer 1)</span>
              <span style={{ color: '#1f77b4', fontWeight: 700 }}>● Target Infra (Layer 2)</span>
            </div>
          </div>
        </div>

        {/* Node Inspector Panel */}
        <div style={{ background: '#fafcfb', border: '1px solid var(--card-border)', borderRadius: '8px', padding: '14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '8px' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-heading)' }}>
              Ego Entity Inspector
            </h4>
            <span className="text-xs text-muted">Degrees of Separation & Relationship Graph</span>
          </div>

          {selectedNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div>
                <span className="detail-label" style={{ fontSize: '0.75rem' }}>Entity Label / ID:</span>
                <div className="font-mono text-bold" style={{ fontSize: '0.875rem', wordBreak: 'break-all' }}>
                  {selectedNode.label}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span className="detail-label" style={{ fontSize: '0.75rem' }}>Ego Layer:</span>
                  <div style={{ marginTop: '2px', fontWeight: 700, fontSize: '0.8125rem' }}>
                    {selectedNode.layer === 0 ? '👑 Center (Layer 0)' : selectedNode.layer === 1 ? '1️⃣ Attack Hop (Layer 1)' : '2️⃣ Infra Endpoint (Layer 2)'}
                  </div>
                </div>

                <div>
                  <span className="detail-label" style={{ fontSize: '0.75rem' }}>Risk Score:</span>
                  <div style={{ marginTop: '2px' }}>
                    <RiskBadge
                      level={(selectedNode.risk_score > 0.7 ? 'HIGH' : selectedNode.risk_score > 0.4 ? 'MEDIUM' : 'LOW') as RiskLevel}
                      score={selectedNode.risk_score}
                    />
                  </div>
                </div>
              </div>

              <div>
                <span className="detail-label" style={{ fontSize: '0.75rem' }}>
                  Direct Ego Links ({connectedLinks.length}):
                </span>
                <div className="edge-list" style={{ marginTop: '6px', maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {connectedLinks.map((l, idx) => (
                    <div key={`${l.source}-${l.target}-${idx}`} className="edge-card" style={{ fontSize: '0.75rem', padding: '6px 8px', display: 'flex', justifyContent: 'space-between' }}>
                      <span className="font-mono">{l.source === selectedNode.id ? 'THIS' : l.source}</span>
                      <span className="edge-relation-badge" style={{ fontSize: '0.7rem' }}>{l.relation}</span>
                      <span className="font-mono">{l.target === selectedNode.id ? 'THIS' : l.target}</span>
                    </div>
                  ))}
                </div>
              </div>

              {selectedNode.type === 'transaction' && onSelectTransaction && selectedNode.id !== data.transaction_id && (
                <button
                  type="button"
                  className="btn-primary"
                  style={{ width: '100%', marginTop: '8px' }}
                  onClick={() => onSelectTransaction(selectedNode.id)}
                >
                  Switch Focus To This Transaction
                </button>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted italic">Click any node in ego network to inspect.</p>
          )}
        </div>
      </div>

      {/* Forensic Intelligence Callout Container */}
      <div
        style={{
          marginTop: '16px',
          padding: '14px 18px',
          background: data.topology_stats?.suspicious_subgraph_nodes > 0 ? '#fef2f2' : '#f0fdf4',
          border: `1px solid ${data.topology_stats?.suspicious_subgraph_nodes > 0 ? '#fecaca' : '#bbf7d0'}`,
          borderRadius: '8px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: data.topology_stats?.suspicious_subgraph_nodes > 0 ? '#991b1b' : '#166534' }}>
            🧠 Network Topology Analysis & Forensic Intelligence
          </h4>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: data.topology_stats?.suspicious_subgraph_nodes > 0 ? '#dc2626' : '#16a34a' }}>
            {data.fraud_pattern}
          </span>
        </div>
        <p style={{ fontSize: '0.8125rem', color: '#334155', margin: 0, lineHeight: 1.5 }}>
          {data.summary || (data.topology_stats?.suspicious_subgraph_nodes > 0
            ? `High-risk clustering detected: Central account is linked to mule recipient via intermediate velocity bursts sharing IP and Hardware GUID. Topology density indicates coordinated syndicate smurfing.`
            : `Isolated baseline pattern: Transaction forms an isolated direct path to known merchant with standard 1st-degree device authorization. No syndicate or mule account overlap detected.`)}
        </p>

        {/* Legend / Badge Strip */}
        <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: `1px solid ${data.topology_stats?.suspicious_subgraph_nodes > 0 ? '#fee2e2' : '#dcfce7'}`, display: 'flex', gap: '12px', flexWrap: 'wrap', fontSize: '0.7rem' }}>
          <span style={{ color: '#059669', fontWeight: 700 }}>🟢 Legitimate Customer (Layer 0)</span>
          <span style={{ color: '#2563eb', fontWeight: 700 }}>🔵 Target Transaction (Layer 1)</span>
          <span style={{ color: '#d97706', fontWeight: 700 }}>🟠 Infrastructure IP (Layer 2)</span>
          <span style={{ color: '#7c3aed', fontWeight: 700 }}>🟣 Hardware GUID (Layer 2)</span>
          <span style={{ color: '#ef4444', fontWeight: 700 }}>🔴 Flagged Mule Sink (Layer 2)</span>
        </div>
      </div>
    </Card>
  )
}

// ============================================================================
// Component 2: Vigil: Temporal IP Fraud Map (With Playback Slider)
// ============================================================================
interface TemporalMapVisualizerProps {
  data: TemporalMapResponse | null
  transactionId: string
}

const TemporalMapVisualizer: React.FC<TemporalMapVisualizerProps> = ({
  data,
  transactionId,
}) => {
  const [activeStep, setActiveStep] = useState<number>(0)
  const [isPlaying, setIsPlaying] = useState<boolean>(false)

  const points = data?.points || data?.trajectory || []
  const violations = data?.velocity_violations || []

  // Automatic playback timer
  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null
    if (isPlaying && points.length > 0) {
      timer = setInterval(() => {
        setActiveStep((prev) => (prev + 1) % points.length)
      }, 1800)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [isPlaying, points.length])

  // Reset step on data change
  useEffect(() => {
    setActiveStep(0)
    setIsPlaying(false)
  }, [data])

  if (!data) {
    return (
      <Card title="Vigil: Temporal IP Fraud Map" subtitle={`Transaction: ${transactionId}`}>
        <div className="empty-module-state">
          <p className="empty-state-title">Loading Geo-Temporal Trajectory...</p>
        </div>
      </Card>
    )
  }

  const activePoint: TemporalMapPoint | undefined = points[activeStep] || points[0]

  // Map projection coordinates to SVG canvas (Equirectangular projection)
  const projectCoords = (lat: number, lon: number) => {
    const x = ((lon + 180) / 360) * 720
    const y = ((90 - lat) / 180) * 380
    return { x, y }
  }

  return (
    <Card
      title="Vigil: Temporal IP Fraud Map"
      subtitle={`Global IP Hop Trajectory & Impossible Travel Velocity Radar (${transactionId})`}
      action={
        <StatusIndicator
          label={data.has_impossible_travel ? `🚨 Impossible Velocity Violations (${violations.length})` : '🟢 Baseline Velocity'}
          variant={data.has_impossible_travel ? 'error' : 'success'}
        />
      }
    >
      {/* World Map SVG Viewport */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '16px' }}>
        <div style={{ position: 'relative', background: '#0f172a', borderRadius: '8px', padding: '12px', overflow: 'hidden' }}>
          <svg width="100%" height="380" viewBox="0 0 720 380" style={{ display: 'block', margin: '0 auto' }}>
            {/* World Continent Outline Rects / Grids */}
            <rect x="0" y="0" width="720" height="380" fill="#0f172a" />
            
            {/* Grid Lines */}
            <line x1="0" y1="190" x2="720" y2="190" stroke="#1e293b" strokeDasharray="3 3" />
            <line x1="360" y1="0" x2="360" y2="380" stroke="#1e293b" strokeDasharray="3 3" />

            {/* Trajectory Hop Path Lines */}
            {points.map((p, idx) => {
              if (idx === 0) return null
              const prev = points[idx - 1]
              const p1 = projectCoords(prev.lat, prev.lon)
              const p2 = projectCoords(p.lat, p.lon)
              const isPassed = idx <= activeStep

              return (
                <g key={`path-${idx}`}>
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke={p.velocity_violation ? '#ef4444' : '#10b981'}
                    strokeWidth={isPassed ? 2.5 : 1}
                    strokeDasharray={p.velocity_violation ? '5 3' : 'none'}
                    strokeOpacity={isPassed ? 1.0 : 0.3}
                  />
                </g>
              )
            })}

            {/* Trajectory IP Points */}
            {points.map((p, idx) => {
              const { x, y } = projectCoords(p.lat, p.lon)
              const isActive = idx === activeStep
              const isPassed = idx <= activeStep

              return (
                <g
                  key={`pt-${idx}`}
                  transform={`translate(${x}, ${y})`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setActiveStep(idx)}
                >
                  {/* Pulse halo for active step */}
                  {isActive && (
                    <circle r="16" fill="none" stroke={p.velocity_violation ? '#ef4444' : '#38bdf8'} strokeWidth="2" opacity="0.8">
                      <animate attributeName="r" values="8;20;8" dur="1.5s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.9;0.2;0.9" dur="1.5s" repeatCount="indefinite" />
                    </circle>
                  )}

                  <circle
                    r={isActive ? 10 : 7}
                    fill={p.velocity_violation ? '#ef4444' : '#10b981'}
                    stroke="#ffffff"
                    strokeWidth="2"
                    opacity={isPassed ? 1.0 : 0.4}
                  />

                  <text x="0" y="-12" textAnchor="middle" fill="#f8fafc" fontSize="10" fontWeight="700">
                    {p.ip}
                  </text>
                  <text x="0" y="20" textAnchor="middle" fill="#94a3b8" fontSize="9">
                    {p.location_name}
                  </text>
                </g>
              )
            })}
          </svg>

          {/* Interactive Time Playback Slider Bar */}
          <div
            style={{
              marginTop: '12px',
              padding: '10px 14px',
              background: '#1e293b',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <button
              type="button"
              className="btn-primary"
              style={{ padding: '6px 12px', fontSize: '0.75rem' }}
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? '⏸️ Pause' : '▶️ Play Trajectory'}
            </button>

            <button
              type="button"
              className="btn-secondary"
              style={{ padding: '6px 10px', fontSize: '0.75rem', background: '#334155', color: '#fff' }}
              onClick={() => {
                setActiveStep(0)
                setIsPlaying(false)
              }}
            >
              🔄 Reset
            </button>

            <input
              type="range"
              min="0"
              max={Math.max(0, points.length - 1)}
              value={activeStep}
              onChange={(e) => {
                setActiveStep(Number(e.target.value))
                setIsPlaying(false)
              }}
              style={{ flex: 1, accentColor: '#38bdf8', cursor: 'pointer' }}
            />

            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'monospace' }}>
              Step {activeStep + 1} / {points.length} ({activePoint?.timestamp || 'N/A'})
            </span>
          </div>
        </div>

        {/* Temporal Velocity Inspector Panel */}
        <div style={{ background: '#fafcfb', border: '1px solid var(--card-border)', borderRadius: '8px', padding: '14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '8px' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-heading)' }}>
              Geo-Velocity Inspector
            </h4>
            <span className="text-xs text-muted">Timestamped IP Travel trajectory</span>
          </div>

          {activePoint ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div>
                <span className="detail-label" style={{ fontSize: '0.75rem' }}>Active IP Address:</span>
                <div className="font-mono text-bold" style={{ fontSize: '0.9375rem', color: '#0f172a' }}>
                  {activePoint.ip}
                </div>
              </div>

              <div>
                <span className="detail-label" style={{ fontSize: '0.75rem' }}>Location & ISP:</span>
                <div className="text-sm font-medium" style={{ color: '#334155' }}>
                  {activePoint.location_name} ({activePoint.isp})
                </div>
              </div>

              <div>
                <span className="detail-label" style={{ fontSize: '0.75rem' }}>Timestamp:</span>
                <div className="font-mono text-xs">{activePoint.timestamp}</div>
              </div>

              <div style={{ padding: '8px 10px', background: activePoint.velocity_violation ? '#fef2f2' : '#f0fdf4', border: `1px solid ${activePoint.velocity_violation ? '#fecaca' : '#bbf7d0'}`, borderRadius: '6px' }}>
                <span className="detail-label" style={{ fontSize: '0.75rem' }}>Calculated Travel Speed:</span>
                <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: activePoint.velocity_violation ? '#dc2626' : '#16a34a' }}>
                  {activePoint.speed_kmh ? `${activePoint.speed_kmh.toLocaleString()} km/h` : '0 km/h (Origin)'}
                </div>
                {activePoint.velocity_violation && (
                  <span style={{ fontSize: '0.7rem', color: '#dc2626', fontWeight: 700, display: 'block', marginTop: '2px' }}>
                    🚨 EXCEEDS 800 KM/H PHYSICAL THRESHOLD
                  </span>
                )}
              </div>

              {violations.length > 0 && (
                <div>
                  <span className="detail-label" style={{ fontSize: '0.75rem' }}>
                    Flagged Velocity Jumps ({violations.length}):
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '4px', maxHeight: '140px', overflowY: 'auto' }}>
                    {violations.map((v, i) => (
                      <div key={i} style={{ padding: '6px 8px', background: '#fff1f2', border: '1px solid #ffe4e6', borderRadius: '4px', fontSize: '0.7rem', color: '#be123c' }}>
                        <strong>{v.from_location} &rarr; {v.to_location}</strong>
                        <div>Speed: {v.speed_kmh.toLocaleString()} km/h ({v.time_delta_minutes} min)</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted italic">Select step on timeline slider.</p>
          )}
        </div>
      </div>

      {/* Geographic Velocity & Hop Analysis Narrative Card */}
      <div
        style={{
          marginTop: '16px',
          padding: '14px 18px',
          background: data.has_impossible_travel ? '#fef2f2' : '#f0fdf4',
          border: `1px solid ${data.has_impossible_travel ? '#fecaca' : '#bbf7d0'}`,
          borderRadius: '8px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: data.has_impossible_travel ? '#991b1b' : '#166534' }}>
            🌍 Geographic Velocity & Hop Analysis
          </h4>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: data.has_impossible_travel ? '#dc2626' : '#16a34a' }}>
            {data.has_impossible_travel ? `🚨 ${violations.length} Impossible Travel Violations` : '🟢 Baseline Physical Velocity'}
          </span>
        </div>
        <p style={{ fontSize: '0.8125rem', color: '#334155', margin: 0, lineHeight: 1.5 }}>
          {data.summary || (data.has_impossible_travel
            ? `Origin hop recorded across a short Delta-T with a calculated velocity of ${data.max_speed_kmh?.toLocaleString()} km/h. Exceeds the 800 km/h physical human velocity threshold, indicating active Tor/VPN IP hop rotation.`
            : `Baseline local trajectory: Geolocation logs confirm physical session proximity within local region across consecutive logins (travel speed: ${data.max_speed_kmh?.toLocaleString()} km/h). No impossible travel velocity violations detected.`)}
        </p>

        {/* Legend / Badge Strip */}
        <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: `1px solid ${data.has_impossible_travel ? '#fee2e2' : '#dcfce7'}`, display: 'flex', gap: '12px', flexWrap: 'wrap', fontSize: '0.7rem' }}>
          <span style={{ color: '#10b981', fontWeight: 700 }}>🟢 Baseline Origin Session</span>
          <span style={{ color: '#38bdf8', fontWeight: 700 }}>🩵 Focus Session Endpoint</span>
          <span style={{ color: '#ef4444', fontWeight: 700 }}>🚨 Red Dashed: Impossible Velocity Hop (&gt;800 km/h)</span>
        </div>
      </div>
    </Card>
  )
}
