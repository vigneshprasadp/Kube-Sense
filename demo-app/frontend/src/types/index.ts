// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TELEMETRY & METRICS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface PodMetric {
  pod: string;
  cpu_cores: number;
  memory_mb: number;
  namespace?: string;
}

export interface PVCMetric {
  pvc_name: string;
  used_mb: number;
  capacity_mb: number;
  percentage_used: number;
  used_bytes?: number;
  capacity_bytes?: number;
}

export interface NetworkLink {
  source_service: string;
  target_service: string;
  latency_ms: number;
  receive_bytes_sec: number;
  transmit_bytes_sec: number;
  tcp_connections: number;
  http_request_rate: number;
  packet_loss_rate: number;
}

export interface Alert {
  id: number;
  pod_name: string;
  cpu_value: number;
  message: string;
  timestamp: string;
  type: 'cpu' | 'storage' | 'network';
}

export interface Telemetry {
  type: string;
  metrics: Record<string, PodMetric>;
  pvc_metrics: PVCMetric[];
  net_metrics: NetworkLink[];
  alerts: Alert[];
  active_rca: RCAReport | null;
  forecasts: Forecast[];
  timestamp: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ROOT CAUSE ANALYSIS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface RCAReport {
  id: number;
  root_cause: string;
  affected_services: string;
  severity: 'Critical' | 'Warning' | 'Info';
  confidence_score: number;
  message: string;
  timestamp: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FORECAST
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface Forecast {
  id: number;
  resource_type: 'cpu' | 'storage' | 'network_latency' | 'network_packet_loss';
  service_name: string;
  current_value: number;
  predicted_value: number;
  threshold: number;
  minutes_to_breach: number | null;
  trend_slope: number;
  r_squared: number;
  severity: 'Critical' | 'Warning' | 'Info';
  message: string;
  created_at?: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DEPENDENCY GRAPH
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface ServiceNode {
  id: string;
  type: string;
  full_name: string;
  status: 'active' | 'warning' | 'error';
  pods: number;
}

export interface ServiceEdge {
  source: string;
  target: string;
}

export interface TopologyData {
  nodes: ServiceNode[];
  edges: ServiceEdge[];
  adjacency: Record<string, string[]>;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// AI RECOMMENDATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface Recommendation {
  id: number;
  rca_id: number;
  root_cause: string;
  severity: string;
  explanation: string;
  recommendations: string[];
  preventive_measures: string[];
  model_used: string;
  created_at: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SETTINGS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface AppSettings {
  apiUrl: string;
  wsUrl: string;
  ollamaModel: string;
  sensitivity: number;
  refreshInterval: number;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UI STATE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export type Severity = 'Critical' | 'Warning' | 'Info' | 'Success';
export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting';
