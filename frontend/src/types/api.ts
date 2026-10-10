export interface HealthResponse {
  status: string
  version: string
  subsystems: {
    ml_screening: string
    database: string
    stream_manager: string
  }
}

export interface Transaction {
  transaction_id: string
  account_id: string
  amount: number
  currency: string
  device_id?: string
  ip?: string
  beneficiary_id?: string
  timestamp: string
  location?: string
  transaction_type?: string
  risk_score?: number
  catboost_score?: number
  status?: string
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | string
}

export interface StreamResponse {
  total: number
  transactions: Transaction[]
}

export interface SimulateAttackResponse {
  status: string
  transaction: Transaction
}

export interface GraphNode {
  id: string
  label: string
  type: string
  layer?: number
  color?: string
  size?: number
  risk_score: number
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
}

export interface GraphTopologyStats {
  total_nodes: number
  total_edges: number
  density: number
  suspicious_subgraph_nodes: number
}

export interface GraphResponse {
  transaction_id: string
  fraud_pattern: string
  summary?: string
  topology_stats: GraphTopologyStats
  nodes: GraphNode[]
  edges: GraphEdge[]
  links?: GraphEdge[]
}

export interface EgoNetworkResponse {
  transaction_id: string
  title: string
  fraud_pattern: string
  summary?: string
  nodes: GraphNode[]
  links: GraphEdge[]
  edges: GraphEdge[]
  topology_stats: GraphTopologyStats
}

export interface TemporalMapPoint {
  ip: string
  lat: number
  lon: number
  timestamp: string
  location_name: string
  country: string
  isp: string
  speed_kmh: number
  distance_km: number
  velocity_violation: boolean
  risk_score: number
}

export interface VelocityViolation {
  from_ip: string
  to_ip: string
  from_location: string
  to_location: string
  time_delta_minutes: number
  distance_km: number
  speed_kmh: number
  threshold_kmh: number
  violation: string
}

export interface TemporalMapResponse {
  transaction_id: string
  title: string
  summary?: string
  points: TemporalMapPoint[]
  trajectory: TemporalMapPoint[]
  velocity_violations: VelocityViolation[]
  max_speed_kmh: number
  has_impossible_travel: boolean
}

export interface EvidenceImpact {
  title: string
  description: string
  impact?: number
}

export interface ExplainabilityDriver {
  feature: string
  value: string
  shap_value: number
}

export interface DossierResponse {
  transaction_id: string
  risk_score: number
  verdict: string
  classification: string
  executive_summary: string
  prosecution_evidence: EvidenceImpact[]
  defense_evidence: EvidenceImpact[]
  explainability_drivers: ExplainabilityDriver[]
}
