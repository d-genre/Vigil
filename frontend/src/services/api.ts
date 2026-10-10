import type {
  HealthResponse,
  StreamResponse,
  SimulateAttackResponse,
  GraphResponse,
  EgoNetworkResponse,
  TemporalMapResponse,
  DossierResponse,
} from '../types/api'

const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown server error')
    throw new ApiError(response.status, `API Error (${response.status}): ${errorText}`)
  }
  return response.json()
}

export const apiService = {
  getBaseUrl(): string {
    return BASE_URL
  },

  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${BASE_URL}/health`)
    return handleResponse<HealthResponse>(res)
  },

  async getStream(tick = false): Promise<StreamResponse> {
    const url = `${BASE_URL}/api/transactions/stream${tick ? '?tick=true' : ''}`
    const res = await fetch(url)
    return handleResponse<StreamResponse>(res)
  },

  async simulateAttack(): Promise<SimulateAttackResponse> {
    const res = await fetch(`${BASE_URL}/api/transactions/simulate-attack`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    return handleResponse<SimulateAttackResponse>(res)
  },

  async getGraph(transactionId: string): Promise<GraphResponse> {
    const res = await fetch(`${BASE_URL}/api/graph/${encodeURIComponent(transactionId)}`)
    return handleResponse<GraphResponse>(res)
  },

  async getEgoNetwork(transactionId: string): Promise<EgoNetworkResponse> {
    const res = await fetch(`${BASE_URL}/api/graph/ego-network/${encodeURIComponent(transactionId)}`)
    return handleResponse<EgoNetworkResponse>(res)
  },

  async getTemporalMap(transactionId: string): Promise<TemporalMapResponse> {
    const res = await fetch(`${BASE_URL}/api/graph/temporal-map/${encodeURIComponent(transactionId)}`)
    return handleResponse<TemporalMapResponse>(res)
  },

  async getDossier(transactionId: string): Promise<DossierResponse> {
    const res = await fetch(`${BASE_URL}/api/dossier/${encodeURIComponent(transactionId)}`)
    return handleResponse<DossierResponse>(res)
  },

  getDossierPdfUrl(transactionId: string): string {
    return `${BASE_URL}/api/dossier/${encodeURIComponent(transactionId)}/pdf`
  },

  async getDbTransactions(limit = 50, offset = 0): Promise<StreamResponse> {
    const res = await fetch(`${BASE_URL}/transactions?limit=${limit}&offset=${offset}`)
    return handleResponse<StreamResponse>(res)
  },
}
