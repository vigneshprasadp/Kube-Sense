import type { Telemetry, ConnectionStatus } from '../types';

type TelemetryCallback = (data: Telemetry) => void;
type StatusCallback = (status: ConnectionStatus) => void;

const getWsUrl = () => {
  if (window.location.hostname === 'localhost') return 'ws://localhost:8000/api/ws/telemetry';
  return `ws://${window.location.host}/api/ws/telemetry`;
};

class WebSocketService {
  private ws: WebSocket | null = null;
  private telemetryListeners: Set<TelemetryCallback> = new Set();
  private statusListeners: Set<StatusCallback> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private active = false;

  connect() {
    this.active = true;
    this.open();
  }

  disconnect() {
    this.active = false;
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
        console.log('[WS] Disconnected. Retrying in 4s...');
        this.notifyStatus('reconnecting');
        if (this.active) {
          this.reconnectTimer = setTimeout(() => this.open(), 4000);
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
