import { useEffect, useState, useCallback } from 'react';
import { Routes, Route } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sidebar } from './components/layout/Sidebar';
import { Navbar } from './components/layout/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Monitoring } from './pages/Monitoring';
import { DependencyGraph } from './pages/DependencyGraph';
import { ForecastPage } from './pages/Forecast';
import { AIInsights } from './pages/AIInsights';
import { wsService } from './services/websocket';
import { apiService } from './services/api';
import { useTelemetry } from './hooks/useTelemetry';
import type { TopologyData, Recommendation, RCAReport, AppSettings } from './types';

const DEFAULT_SETTINGS: AppSettings = {
  apiUrl: window.location.hostname === 'localhost' ? 'http://localhost:8000' : '',
  wsUrl: window.location.hostname === 'localhost' ? 'ws://localhost:8000/api/ws/telemetry' : `ws://${window.location.host}/api/ws/telemetry`,
  ollamaModel: 'llama3.1:latest',
  sensitivity: 2.0,
  refreshInterval: 10,
};

export default function App() {
  const { telemetry, status, lastUpdate } = useTelemetry();

  const [topology, setTopology] = useState<TopologyData>({ nodes: [], edges: [], adjacency: {} });
  const [rcaHistory, setRcaHistory] = useState<RCAReport[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [generatingRecommend, setGeneratingRecommend] = useState(false);
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const saved = localStorage.getItem('kubesense_settings');
      return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS;
    } catch { return DEFAULT_SETTINGS; }
  });

  // Connect WebSocket on mount
  useEffect(() => {
    wsService.connect();
    return () => wsService.disconnect();
  }, []);

  // REST polling loop
  const fetchData = useCallback(async () => {
    try {
      const [topo, rca, rec] = await Promise.allSettled([
        apiService.getDependencies(),
        apiService.getRCAHistory(),
        apiService.getLatestRecommendation(),
      ]);
      if (topo.status === 'fulfilled') setTopology(topo.value);
      if (rca.status === 'fulfilled') setRcaHistory(rca.value);
      if (rec.status === 'fulfilled') setRecommendation(rec.value);
    } catch { /* silent — WS status dot already shows disconnected */ }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, (settings.refreshInterval || 10) * 1000);
    return () => clearInterval(id);
  }, [fetchData, settings.refreshInterval]);

  const handleGenerateRecommendation = async (rcaId?: number) => {
    setGeneratingRecommend(true);
    try {
      const rec = await apiService.generateRecommendation(rcaId);
      if (rec) setRecommendation(rec);
    } catch { /* noop */ }
    finally { setGeneratingRecommend(false); }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar status={status} />

      {/* Main content — offset by sidebar width */}
      <div className="flex-1 flex flex-col" style={{ marginLeft: 'calc(var(--sidebar-width) + 12px)' }}>
        <Navbar status={status} />

        <motion.main
          className="flex-1 px-6 pb-8 overflow-y-auto"
          style={{ marginTop: 'var(--navbar-height)', paddingTop: 28 }}
        >
          <Routes>
            <Route path="/" element={<Dashboard telemetry={telemetry} />} />
            <Route path="/monitoring" element={<Monitoring telemetry={telemetry} />} />
            <Route path="/topology" element={<DependencyGraph topology={topology} telemetry={telemetry} />} />
            <Route path="/forecast" element={<ForecastPage forecasts={telemetry.forecasts || []} />} />
            <Route path="/insights" element={
              <AIInsights
                recommendation={recommendation}
                activeRca={telemetry.active_rca}
                generatingRecommend={generatingRecommend}
                onGenerate={handleGenerateRecommendation}
              />
            } />
          </Routes>
        </motion.main>
      </div>
    </div>
  );
}
