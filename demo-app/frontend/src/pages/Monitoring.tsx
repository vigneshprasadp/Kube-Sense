import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, HardDrive, Wifi } from 'lucide-react';
import { AreaMetricChart } from '../components/charts/AreaMetricChart';
import type { Telemetry } from '../types';

const TABS = [
  { id: 'cpu',     label: 'CPU',     icon: Cpu },
  { id: 'storage', label: 'Storage', icon: HardDrive },
  { id: 'network', label: 'Network', icon: Wifi },
];

interface MonitoringProps { telemetry: Telemetry; }

export function Monitoring({ telemetry }: MonitoringProps) {
  const [tab, setTab] = useState('cpu');
  const { metrics, pvc_metrics, net_metrics } = telemetry;
  const pods = Object.entries(metrics);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="page-header-title">Monitoring</h2>
        <p className="page-header-subtitle">Deep-dive resource metrics across all cluster services</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1.5 bg-surface-100/70 rounded-2xl w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-600 transition-all
              ${tab === id ? 'bg-white text-brand-700 shadow-card' : 'text-surface-500 hover:text-surface-700'}`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }}>

          {/* CPU Tab */}
          {tab === 'cpu' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {pods.map(([pod, m]) => (
                  <div key={pod} className="solid-card p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-600 text-surface-500 uppercase tracking-wider truncate">{pod.split('-')[0]}</span>
                      <Cpu className="h-4 w-4 text-brand-400" />
                    </div>
                    <p className="metric-value text-xl">{m.cpu_cores?.toFixed(4)}</p>
                    <p className="text-xs text-surface-400 mt-1 font-500">cores · {m.memory_mb?.toFixed(0)} MB RAM</p>
                    <div className="mt-3 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                      <div className="h-full bg-brand-500 rounded-full transition-all" style={{ width: `${Math.min(100, (m.cpu_cores || 0) * 1000)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="solid-card p-6">
                <h3 className="text-sm font-700 text-surface-800 mb-4">CPU Utilization Over Time</h3>
                <AreaMetricChart data={pods.map(([p, m]) => ({ name: p.split('-')[0].toUpperCase(), cores: +(m.cpu_cores || 0).toFixed(4), mem: +(m.memory_mb || 0).toFixed(0) }))}
                  dataKey="cores" secondKey="mem" color="#0D9488" secondColor="#7C3AED" height={260} />
              </div>
            </div>
          )}

          {/* Storage Tab */}
          {tab === 'storage' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {pvc_metrics.length === 0 ? (
                  <div className="col-span-3 flex justify-center items-center h-40 text-surface-300">No PVC data available</div>
                ) : pvc_metrics.map(pvc => {
                  const pct = pvc.percentage_used;
                  const color = pct > 85 ? 'bg-danger-500' : pct > 65 ? 'bg-warning-500' : 'bg-success-500';
                  const textColor = pct > 85 ? 'text-danger-600' : pct > 65 ? 'text-warning-600' : 'text-success-600';
                  return (
                    <div key={pvc.pvc_name} className="solid-card p-6">
                      <div className="flex items-center justify-between mb-3">
                        <p className="text-sm font-700 text-surface-800 truncate">{pvc.pvc_name}</p>
                        <HardDrive className="h-4 w-4 text-surface-300" />
                      </div>
                      <p className={`text-3xl font-700 tracking-tight mb-1 ${textColor}`}>{pct.toFixed(1)}%</p>
                      <p className="text-xs text-surface-400 mb-3">{pvc.used_mb?.toFixed(0)} MB / {pvc.capacity_mb?.toFixed(0)} MB</p>
                      <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="solid-card p-6">
                <h3 className="text-sm font-700 text-surface-800 mb-4">Storage Saturation Overview</h3>
                <AreaMetricChart
                  data={pvc_metrics.map(p => ({ name: p.pvc_name, used: +p.percentage_used.toFixed(1) }))}
                  dataKey="used" color="#7C3AED" unit="%" height={240} />
              </div>
            </div>
          )}

          {/* Network Tab */}
          {tab === 'network' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: 'Active Links', value: net_metrics.length, sub: 'service connections', color: 'text-brand-600' },
                  { label: 'Avg Latency',  value: net_metrics.length ? (net_metrics.reduce((s, l) => s + l.latency_ms, 0) / net_metrics.length).toFixed(0) + 'ms' : '—', sub: 'across all links', color: 'text-surface-900' },
                  { label: 'Total Conns',  value: net_metrics.reduce((s, l) => s + l.tcp_connections, 0), sub: 'TCP connections', color: 'text-surface-900' },
                ].map(c => (
                  <div key={c.label} className="solid-card p-5">
                    <p className="metric-label mb-2">{c.label}</p>
                    <p className={`text-3xl font-700 tracking-tight ${c.color}`}>{c.value}</p>
                    <p className="text-xs text-surface-400 mt-1">{c.sub}</p>
                  </div>
                ))}
              </div>
              <div className="solid-card p-6 overflow-x-auto">
                <h3 className="text-sm font-700 text-surface-800 mb-4">Service Communication Details</h3>
                {net_metrics.length === 0 ? <div className="text-center text-surface-300 py-10">No network data</div> : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-surface-100">
                        {['Source','Target','Latency','RX kB/s','TX kB/s','TCP','HTTP/s','Pkt Loss'].map(h => (
                          <th key={h} className="pb-3 text-left text-xs font-600 text-surface-400 uppercase tracking-wider pr-4">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-50">
                      {net_metrics.map((l, i) => (
                        <tr key={i} className="table-row-hover">
                          <td className="py-3 pr-4 font-600 text-surface-800 text-xs">{l.source_service}</td>
                          <td className="py-3 pr-4 text-xs text-surface-600">{l.target_service}</td>
                          <td className="py-3 pr-4">
                            <span className={`text-xs font-700 px-2 py-0.5 rounded-lg ${l.latency_ms > 500 ? 'bg-danger-50 text-danger-600' : l.latency_ms > 200 ? 'bg-warning-50 text-warning-600' : 'bg-success-50 text-success-600'}`}>
                              {l.latency_ms.toFixed(0)}ms
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-xs text-surface-600">{((l.receive_bytes_sec || 0) / 1024).toFixed(1)}</td>
                          <td className="py-3 pr-4 text-xs text-surface-600">{((l.transmit_bytes_sec || 0) / 1024).toFixed(1)}</td>
                          <td className="py-3 pr-4 text-xs text-surface-600">{l.tcp_connections}</td>
                          <td className="py-3 pr-4 text-xs text-surface-600">{l.http_request_rate?.toFixed(1)}</td>
                          <td className="py-3 text-xs font-600 text-danger-600">{l.packet_loss_rate > 0 ? `${l.packet_loss_rate.toFixed(2)}%` : <span className="text-success-600">0%</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
