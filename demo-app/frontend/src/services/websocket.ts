import type { Telemetry, ConnectionStatus } from '../types';

type TelemetryCallback = (data: Telemetry) => void;
type StatusCallback = (status: ConnectionStatus) => void;

const getWsUrl = () => {
  if (window.location.port === '5173') return 'ws://localhost:8000/api/ws/telemetry';
  return `ws://${window.location.host}/api/ws/telemetry`;
};

class WebSocketService {
  private ws: WebSocket | null = null;
  private telemetryListeners: Set<TelemetryCallback> = new Set();
  private statusListeners: Set<StatusCallback> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private active = false;
  private retryCount = 0;

  connect() {
    this.active = true;
    this.retryCount = 0;
    this.open();
  }

  disconnect() {
    this.active = false;
    this.retryCount = 0;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.notifyStatus('disconnected');
  }

  onTelemetry(cb: TelemetryCallback) {
    this.telemetryListeners.add(cb);
    return () => this.telemetryListeners.delete(cb);
  }

  onStatus(cb: StatusCallback) {
    this.statusListeners.add(cb);
    return () => this.statusListeners.delete(cb);
  }

  private open() {
    if (!this.active) return;
    try {
      this.ws = new WebSocket(getWsUrl());

      this.ws.onopen = () => {
        console.log('[WS] Connected');
        this.retryCount = 0;
        this.notifyStatus('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as Telemetry;
          if (payload.type === 'telemetry') {
            this.telemetryListeners.forEach(cb => cb(payload));
          }
        } catch (e) {
          console.warn('[WS] Parse error', e);
        }
      };

      this.ws.onclose = () => {
        // Exponential backoff: 1s → 1.5s → 2.25s → max 5s
        const delay = Math.min(1000 * Math.pow(1.5, Math.min(this.retryCount, 3)), 5000);
        this.retryCount++;
        console.log(`[WS] Disconnected. Retrying in ${Math.round(delay)}ms... (attempt ${this.retryCount})`);
        this.notifyStatus('reconnecting');
        if (this.active) {
          this.reconnectTimer = setTimeout(() => this.open(), delay);
        }
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      this.notifyStatus('disconnected');
    }
  }

  private notifyStatus(status: ConnectionStatus) {
    this.statusListeners.forEach(cb => cb(status));
  }
}

export const wsService = new WebSocketService();
