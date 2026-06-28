import axios from 'axios';
import type { TopologyData, RCAReport, Recommendation, Forecast, Alert } from '../types';

// Detect environment: in K8s the frontend proxies /api to backend service
const getBaseUrl = () => {
  if (window.location.port === '5173') return 'http://localhost:8000';
  return ''; // nginx proxies /api → backend-service:8000
};

export const api = axios.create({
  baseURL: getBaseUrl(),
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// API METHODS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export const apiService = {
  getDependencies: async (): Promise<TopologyData> => {
    const { data } = await api.get('/api/dependencies');
    return data;
  },

  getRCAHistory: async (): Promise<RCAReport[]> => {
    const { data } = await api.get('/api/rca');
    return Array.isArray(data) ? data : [];
  },

  getActiveRCA: async (): Promise<RCAReport | null> => {
    try {
      const { data } = await api.get('/api/rca/active');
      return data?.id ? data : null;
    } catch {
      return null;
    }
  },

  getForecasts: async (): Promise<Forecast[]> => {
    const { data } = await api.get('/api/forecasts');
    return Array.isArray(data) ? data : [];
  },

  getAlerts: async (): Promise<Alert[]> => {
    const { data } = await api.get('/api/alerts');
    return Array.isArray(data) ? data : [];
  },

  getLatestRecommendation: async (): Promise<Recommendation | null> => {
    try {
      const { data } = await api.get('/api/recommendations/latest');
      return data?.id ? data : null;
    } catch {
      return null;
    }
  },

  generateRecommendation: async (rcaId?: number): Promise<Recommendation | null> => {
    const url = rcaId
      ? `/api/recommendations/generate?rca_id=${rcaId}`
      : '/api/recommendations/generate';
    const { data } = await api.post(url);
    return data?.id ? data : null;
  },

  getChaosTemplates: async (): Promise<string[]> => {
    const { data } = await api.get('/api/chaos/templates');
    return data;
  },

  getActiveChaosEvents: async (): Promise<any[]> => {
    const { data } = await api.get('/api/chaos/events');
    return data;
  },

  startChaos: async (type: string, target: string, severity: string): Promise<any> => {
    const { data } = await api.post('/api/chaos/start', { type, target, severity });
    return data;
  },

  stopChaos: async (eventId: string): Promise<any> => {
    const { data } = await api.post('/api/chaos/stop', { event_id: eventId });
    return data;
  },

  getChaosRca: async (): Promise<any> => {
    try {
      const { data } = await api.get('/api/chaos/rca');
      return data;
    } catch {
      return null;
    }
  },
};
