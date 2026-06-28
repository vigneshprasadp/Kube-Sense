import { motion } from 'framer-motion';
import { AlertTriangle, Cpu, HardDrive, Wifi, Server, Heart, ShieldAlert, ArrowRight, CheckCircle, Activity } from 'lucide-react';
import { AreaMetricChart } from '../components/charts/AreaMetricChart';
import { MetricCard } from '../components/cards/MetricCard';
import { Badge } from '../components/common/Badge';
import { useNavigate } from 'react-router-dom';
import type { Telemetry, RCAReport } from '../types';

interface DashboardProps { telemetry: Telemetry; chaosRca: RCAReport | null; }

export function Dashboard({ telemetry, chaosRca }: DashboardProps) {
  const navigate = useNavigate();
  const { metrics, pvc_metrics, net_metrics, alerts, forecasts } = telemetry;

  const pods = Object.keys(metrics);
  const totalCpu = pods.reduce((s, p) => s + (metrics[p]?.cpu_cores || 0), 0);
  const avgStorage = pvc_metrics.length > 0 ? pvc_metrics.reduce((s, p) => s + p.percentage_used, 0) / pvc_metrics.length : 0;
  const avgLatency = net_metrics.length > 0 ? net_metrics.reduce((s, l) => s + l.latency_ms, 0) / net_metrics.length : 0;
  const criticalForecasts = forecasts.filter(f => f.severity === 'Critical' && f.minutes_to_breach !== null).length;

  const cpuData = pods.map(p => ({ name: p.split('-')[0].toUpperCase(), cores: +(metrics[p]?.cpu_cores || 0).toFixed(4) }));
  const storageData = pvc_metrics.map(p => ({ name: p.pvc_name.replace('postgres-', ''), used: +p.percentage_used.toFixed(1), free: +(100 - p.percentage_used).toFixed(1) }));

  const isChaosActive = !!(chaosRca && chaosRca.chaos_active);

  const summaryCards = [
    { label: 'Running Pods',    value: pods.length || 4, unit: 'pods',   icon: <Server className="h-5 w-5" />,        iconBg: 'bg-brand-50 text-brand-600',   subtitle: 'tasksphere-app namespace' },
    { label: 'Healthy Services',value: isChaosActive ? 3 : 4, unit: '',    icon: <Heart className="h-5 w-5" />,         iconBg: isChaosActive ? 'bg-danger-50 text-danger-600' : 'bg-success-50 text-success-600', subtitle: isChaosActive ? '1 service degraded' : 'All services normal', valueColor: isChaosActive ? 'text-danger-600' : 'text-success-600' },
    { label: 'Total CPU',       value: totalCpu.toFixed(4), unit: 'cores', icon: <Cpu className="h-5 w-5" />,       iconBg: 'bg-purple-50 text-purple-600',  subtitle: `${pods.length} pods measured` },
    { label: 'Avg. Storage',    value: avgStorage.toFixed(1), unit: '%', icon: <HardDrive className="h-5 w-5" />,  iconBg: 'bg-cyan-50 text-cyan-600',      subtitle: `${pvc_metrics.length} PVCs monitored`, valueColor: avgStorage > 80 ? 'text-danger-600' : avgStorage > 60 ? 'text-warning-600' : 'text-surface-900' },
    { label: 'Avg. Latency',    value: avgLatency.toFixed(0), unit: 'ms',icon: <Wifi className="h-5 w-5" />,      iconBg: 'bg-orange-50 text-orange-600',  subtitle: `${net_metrics.length} links`, valueColor: avgLatency > 500 ? 'text-danger-600' : 'text-surface-900' },
    { label: 'Active Incidents', value: isChaosActive ? alerts.length || 1 : 0, unit: '',  icon: <ShieldAlert className="h-5 w-5" />, iconBg: isChaosActive ? 'bg-danger-50 text-danger-600' : 'bg-success-50 text-success-600', subtitle: isChaosActive ? 'Simulation running' : 'No active incidents', valueColor: isChaosActive ? 'text-danger-600' : 'text-success-600' },
  ];

  return (
    <div className="space-y-6">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="solid-card p-8 bg-gradient-to-r from-brand-600 via-brand-500 to-cyan-500 text-white overflow-hidden relative"
        style={{ borderRadius: '1.5rem' }}
      >
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 70% 50%, white 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
        <div className="relative flex items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-5 w-5 opacity-80" />
              <span className="text-sm font-500 opacity-80 uppercase tracking-wider">KubeSense AI Platform</span>
            </div>
            <h2 className="text-3xl font-700 tracking-tight mb-1">Cluster Status</h2>
            <p className="text-white/70 text-sm mb-4">AI-Powered Kubernetes Observability · Minikube · tasksphere-app</p>
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-600 ${isChaosActive ? 'bg-red-500/30 border border-red-400/40' : 'bg-white/20 border border-white/30'}`}>
                {isChaosActive ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle className="h-4 w-4" />}
                {isChaosActive ? 'Incident Detected' : 'All Systems Healthy'}
              </span>
              <span className="text-white/60 text-sm">{pods.length} pods · {pvc_metrics.length} volumes · {net_metrics.length} links</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Root Cause Banner */}
      {chaosRca && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className={`p-5 rounded-2xl flex items-start justify-between gap-4 border ${
            chaosRca.chaos_active
              ? 'bg-gradient-to-r from-red-50 to-rose-50 border-red-200 text-red-950 shadow-sm shadow-red-500/5'
              : 'bg-gradient-to-r from-surface-50 to-white border-surface-200 text-surface-800 shadow-sm shadow-surface-900/5'
          }`}
          style={{
            borderLeftWidth: 4,
            borderLeftColor: chaosRca.chaos_active ? '#DC2626' : '#64748B'
          }}
        >
          <div className="flex gap-3">
            <div className={`p-2 rounded-xl flex-shrink-0 mt-0.5 ${
              chaosRca.chaos_active ? 'bg-red-100' : 'bg-surface-100'
            }`}>
              <ShieldAlert className={`h-5 w-5 ${
                chaosRca.chaos_active ? 'text-danger-600' : 'text-surface-500'
              }`} />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-sm font-700 ${
                  chaosRca.chaos_active ? 'text-danger-800' : 'text-surface-800'
                }`}>
                  {chaosRca.chaos_active ? 'Root Cause Analysis — Active Incident' : 'Root Cause Analysis — Last Incident'}
                </span>
                <Badge severity={chaosRca.chaos_active ? 'Critical' : 'Info'} size="sm" />
              </div>
              <p className={`text-sm font-600 ${
                chaosRca.chaos_active ? 'text-danger-700' : 'text-surface-750'
              }`}>{chaosRca.root_cause}</p>
              <p className={`text-xs mt-1 leading-relaxed ${
                chaosRca.chaos_active ? 'text-danger-600' : 'text-surface-500'
              }`}>{chaosRca.message?.slice(0, 160)}...</p>
              <div className={`flex items-center gap-4 mt-2 text-xs font-500 ${
                chaosRca.chaos_active ? 'text-danger-600' : 'text-surface-500'
              }`}>
                <span>Affected: <strong>{chaosRca.affected_services}</strong></span>
                <span>Confidence: <strong>{Math.round(chaosRca.confidence_score * 100)}%</strong></span>
              </div>
            </div>
          </div>
          <button onClick={() => navigate('/insights')}
            className={`flex-shrink-0 flex items-center gap-2 px-4 py-2 text-white text-sm font-600 rounded-xl transition-colors ${
              chaosRca.chaos_active ? 'bg-danger-600 hover:bg-danger-700' : 'bg-surface-600 hover:bg-surface-700'
            }`}>
            AI Analysis <ArrowRight className="h-4 w-4" />
          </button>
        </motion.div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {summaryCards.map((c, i) => (
          <MetricCard key={c.label} {...c} index={i} />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="solid-card p-6">
          <h3 className="text-sm font-700 text-surface-800 mb-1">CPU Allocation by Pod</h3>
          <p className="text-xs text-surface-400 mb-4">Live CPU core consumption per active pod</p>
          <AreaMetricChart data={cpuData} dataKey="cores" color="#0D9488" unit=" cores" height={200} />
        </div>
        <div className="solid-card p-6">
          <h3 className="text-sm font-700 text-surface-800 mb-1">Storage Utilization</h3>
          <p className="text-xs text-surface-400 mb-4">PVC used vs available capacity (%)</p>
          <AreaMetricChart data={storageData} dataKey="used" secondKey="free" color="#7C3AED" secondColor="#E2E8F0" unit="%" height={200} />
        </div>
      </div>

      {/* Network + Alerts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Network Table */}
        <div className="lg:col-span-5 solid-card p-6">
          <h3 className="text-sm font-700 text-surface-800 mb-1">Network Communication</h3>
          <p className="text-xs text-surface-400 mb-4">Live service-to-service link telemetry</p>
          {net_metrics.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-surface-300 text-sm">No network data yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-100">
                    {['Link', 'Latency', 'Throughput', 'Conns', 'HTTP Rate', 'Loss'].map(h => (
                      <th key={h} className="pb-3 text-left text-xs font-600 text-surface-400 uppercase tracking-wider pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-50">
                  {net_metrics.map((l, i) => (
                    <tr key={i} className="table-row-hover">
                      <td className="py-3 pr-4 font-600 text-surface-800 text-xs">{l.source_service}<span className="text-surface-300 mx-1">→</span>{l.target_service}</td>
                      <td className="py-3 pr-4">
                        <span className={`text-xs font-600 ${l.latency_ms > 500 ? 'text-danger-600' : l.latency_ms > 200 ? 'text-warning-600' : 'text-success-600'}`}>
                          {l.latency_ms.toFixed(0)}ms
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-xs text-surface-600">{(((l.receive_bytes_sec || 0) + (l.transmit_bytes_sec || 0)) / 1024).toFixed(1)} kB/s</td>
                      <td className="py-3 pr-4 text-xs text-surface-600">{l.tcp_connections}</td>
                      <td className="py-3 pr-4 text-xs text-surface-600">{l.http_request_rate?.toFixed(1)} req/s</td>
                      <td className="py-3">
                        <span className={`text-xs font-600 ${l.packet_loss_rate > 0 ? 'text-danger-600' : 'text-success-600'}`}>
                          {l.packet_loss_rate > 0 ? `${l.packet_loss_rate.toFixed(2)}%` : '0%'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
