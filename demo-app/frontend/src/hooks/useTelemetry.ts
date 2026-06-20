import { useState, useEffect, useCallback } from 'react';
import { wsService } from '../services/websocket';
import type { Telemetry, ConnectionStatus } from '../types';

const defaultTelemetry: Telemetry = {
  type: 'telemetry',
  metrics: {},
  pvc_metrics: [],
  net_metrics: [],
  alerts: [],
  active_rca: null,
  forecasts: [],
  timestamp: '',
};

export function useTelemetry() {
  const [telemetry, setTelemetry] = useState<Telemetry>(defaultTelemetry);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const handleTelemetry = useCallback((data: Telemetry) => {
    setTelemetry(data);
    setLastUpdate(new Date());
  }, []);

  useEffect(() => {
    const unsubTelemetry = wsService.onTelemetry(handleTelemetry);
    const unsubStatus = wsService.onStatus(setStatus);
    return () => {
      unsubTelemetry();
      unsubStatus();
    };
  }, [handleTelemetry]);

  return { telemetry, status, lastUpdate };
}
