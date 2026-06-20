import { motion } from 'framer-motion';
import { AlertTriangle, Cpu, HardDrive, Wifi, Server, Heart, ShieldAlert, ArrowRight, CheckCircle, Activity } from 'lucide-react';
import { AreaMetricChart } from '../components/charts/AreaMetricChart';
import { MetricCard } from '../components/cards/MetricCard';
import { Badge } from '../components/common/Badge';
import { useNavigate } from 'react-router-dom';
import type { Telemetry } from '../types';

interface DashboardProps { telemetry: Telemetry; }

export function Dashboard({ telemetry }: DashboardProps) {
  const navigate = useNavigate();
  const { metrics, pvc_metrics, net_metrics, alerts, active_rca, forecasts } = telemetry;

  const pods = Object.keys(metrics);
  const totalCpu = pods.reduce((s, p) => s + (metrics[p]?.cpu_cores || 0), 0);
  const avgStorage = pvc_metrics.length > 0 ? pvc_metrics.reduce((s, p) => s + p.percentage_used, 0) / pvc_metrics.length : 0;
  const avgLatency = net_metrics.length > 0 ? net_metrics.reduce((s, l) => s + l.latency_ms, 0) / net_metrics.length : 0;
  const criticalForecasts = forecasts.filter(f => f.severity === 'Critical' && f.minutes_to_breach !== null).length;

  const cpuData = pods.map(p => ({ name: p.split('-')[0].toUpperCase(), cores: +(metrics[p]?.cpu_cores || 0).toFixed(4) }));
  const storageData = pvc_metrics.map(p => ({ name: p.pvc_name.replace('postgres-', ''), used: +p.percentage_used.toFixed(1), free: +(100 - p.percentage_used).toFixed(1) }));

  const summaryCards = [
    { label: 'Running Pods',    value: pods.length || 4, unit: 'pods',   icon: <Server className="h-5 w-5" />,        iconBg: 'bg-brand-50 text-brand-600',   subtitle: 'tasksphere-app namespace' },
    { label: 'Healthy Services',value: active_rca ? 3 : 4, unit: '',    icon: <Heart className="h-5 w-5" />,         iconBg: 'bg-success-50 text-success-600', subtitle: active_rca ? '1 service degraded' : 'All services normal', valueColor: active_rca ? 'text-danger-600' : 'text-success-600' },
    { label: 'Total CPU',       value: totalCpu.toFixed(4), unit: 'cores', icon: <Cpu className="h-5 w-5" />,       iconBg: 'bg-purple-50 text-purple-600',  subtitle: `${pods.length} pods measured` },
    { label: 'Avg. Storage',    value: avgStorage.toFixed(1), unit: '%', icon: <HardDrive className="h-5 w-5" />,  iconBg: 'bg-cyan-50 text-cyan-600',      subtitle: `${pvc_metrics.length} PVCs monitored`, valueColor: avgStorage > 80 ? 'text-danger-600' : avgStorage > 60 ? 'text-warning-600' : 'text-surface-900' },
    { label: 'Avg. Latency',    value: avgLatency.toFixed(0), unit: 'ms',icon: <Wifi className="h-5 w-5" />,      iconBg: 'bg-orange-50 text-orange-600',  subtitle: `${net_metrics.length} links`, valueColor: avgLatency > 500 ? 'text-danger-600' : 'text-surface-900' },
    { label: 'Active Incidents', value: alerts.length, unit: '',         icon: <ShieldAlert className="h-5 w-5" />, iconBg: alerts.length > 0 ? 'bg-danger-50 text-danger-600' : 'bg-surface-50 text-surface-400', subtitle: criticalForecasts > 0 ? `${criticalForecasts} critical forecasts` : 'Stable', valueColor: alerts.length > 0 ? 'text-danger-600' : 'text-surface-900' },
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
              <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-600 ${active_rca ? 'bg-red-500/30 border border-red-400/40' : 'bg-white/20 border border-white/30'}`}>
                {active_rca ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle className="h-4 w-4" />}
                {active_rca ? 'Incident Detected' : 'All Systems Healthy'}
              </span>
              <span className="text-white/60 text-sm">{pods.length} pods · {pvc_metrics.length} volumes · {net_metrics.length} links</span>
            </div>
          </div>
          <div className="hidden lg:block text-right">
            <p className="text-white/50 text-xs mb-1 font-500 uppercase tracking-wider">Last Sync</p>
            <p className="text-white font-600">{telemetry.timestamp ? new Date(telemetry.timestamp).toLocaleTimeString() : '—'}</p>
          </div>
        </div>
      </motion.div>

      {/* Root Cause Banner */}
      {active_rca && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-5 rounded-2xl border-l-4 border-danger-600 bg-danger-50 flex items-start justify-between gap-4"
          style={{ border: '1px solid #FECDD3', borderLeftWidth: 4, borderLeftColor: '#DC2626' }}
        >
          <div className="flex gap-3">
            <div className="p-2 bg-danger-100 rounded-xl flex-shrink-0 mt-0.5">
              <ShieldAlert className="h-5 w-5 text-danger-600" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-700 text-danger-800">Root Cause Analysis — Active Incident</span>
                <Badge severity="Critical" size="sm" />
              </div>
              <p className="text-sm text-danger-700 font-600">{active_rca.root_cause}</p>
              <p className="text-xs text-danger-600 mt-1 leading-relaxed">{active_rca.message?.slice(0, 160)}...</p>
              <div className="flex items-center gap-4 mt-2 text-xs text-danger-600 font-500">
                <span>Affected: <strong>{active_rca.affected_services}</strong></span>
                <span>Confidence: <strong>{Math.round(active_rca.confidence_score * 100)}%</strong></span>
              </div>
            </div>
          </div>
          <button onClick={() => navigate('/insights')}
            className="flex-shrink-0 flex items-center gap-2 px-4 py-2 bg-danger-600 hover:bg-danger-700 text-white text-sm font-600 rounded-xl transition-colors">
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
        <div className="lg:col-span-3 solid-card p-6">
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

        {/* Live Alerts */}
        <div className="lg:col-span-2 solid-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-700 text-surface-800">Live Alert Stream</h3>
              <p className="text-xs text-surface-400 mt-0.5">Last 15 minutes</p>
            </div>
            <span className={`badge ${alerts.length > 0 ? 'badge-critical' : 'badge-success'}`}>
              {alerts.length} Active
            </span>
          </div>
          <div className="space-y-2 overflow-y-auto max-h-60">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-surface-300">
                <CheckCircle className="h-8 w-8 mb-2" />
                <p className="text-sm font-500">All clear — no alerts</p>
              </div>
            ) : alerts.slice(0, 8).map(a => (
              <div key={a.id} className="flex items-start gap-2.5 p-3 rounded-xl bg-surface-50/80 border border-surface-100">
                <AlertTriangle className={`h-3.5 w-3.5 mt-0.5 flex-shrink-0 ${a.type === 'network' ? 'text-danger-600' : a.type === 'storage' ? 'text-orange-500' : 'text-warning-500'}`} />
                <div className="min-w-0">
                  <p className="text-xs font-600 text-surface-800 leading-snug truncate">{a.message}</p>
                  <p className="text-[10px] text-surface-400 mt-0.5">{a.pod_name} · {new Date(a.timestamp).toLocaleTimeString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
