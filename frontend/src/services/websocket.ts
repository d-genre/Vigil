import type { Transaction } from '../types/api'

export interface WsScreenedEvent {
  event_type: 'TRANSACTION_SCREENED'
  data: Transaction
}

export type WsStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR'

class WebSocketService {
  private socket: WebSocket | null = null
  private listeners: Array<(event: WsScreenedEvent) => void> = []
  private statusListeners: Array<(status: WsStatus) => void> = []
  private status: WsStatus = 'DISCONNECTED'
  private reconnectTimer: number | null = null

  private getWsUrl(): string {
    const baseUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws'
    const host = baseUrl.replace(/^https?:\/\//, '')
    return `${wsProtocol}://${host}/ws/live`
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.setStatus('CONNECTING')
    const url = this.getWsUrl()

    try {
      this.socket = new WebSocket(url)

      this.socket.onopen = () => {
        this.setStatus('CONNECTED')
      }

      this.socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as WsScreenedEvent
          if (parsed && parsed.event_type === 'TRANSACTION_SCREENED') {
            this.listeners.forEach((cb) => cb(parsed))
          }
        } catch {
          // Ignore non-JSON or unhandled messages
        }
      }

      this.socket.onerror = () => {
        this.setStatus('ERROR')
      }

      this.socket.onclose = () => {
        this.setStatus('DISCONNECTED')
        this.scheduleReconnect()
      }
    } catch {
      this.setStatus('ERROR')
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, 5000)
  }

  private setStatus(newStatus: WsStatus): void {
    this.status = newStatus
    this.statusListeners.forEach((cb) => cb(newStatus))
  }

  public getStatus(): WsStatus {
    return this.status
  }

  public subscribe(cb: (event: WsScreenedEvent) => void): () => void {
    this.listeners.push(cb)
    return () => {
      this.listeners = this.listeners.filter((l) => l !== cb)
    }
  }

  public subscribeStatus(cb: (status: WsStatus) => void): () => void {
    this.statusListeners.push(cb)
    cb(this.status)
    return () => {
      this.statusListeners = this.statusListeners.filter((l) => l !== cb)
    }
  }

  public disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
    this.setStatus('DISCONNECTED')
  }
}

export const wsService = new WebSocketService()
