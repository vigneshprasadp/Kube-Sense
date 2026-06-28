import { useState, useCallback, useEffect } from 'react';
import ReactFlow, { Background, Controls, useNodesState, useEdgesState, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Server, Network, Cpu, HardDrive } from 'lucide-react';
import { ServiceNodeComponent } from '../components/graph/ServiceNode';
import { apiService } from '../services/api';
import type { TopologyData, ServiceNode } from '../types';

const nodeTypes = { service: ServiceNodeComponent };

const POSITIONS: Record<string, { x: number; y: number }> = {
  frontend:   { x: 300, y: 60  },
  backend:    { x: 300, y: 220 },
  database:   { x: 300, y: 380 },
  prometheus: { x: 620, y: 220 },
};

interface DependencyGraphProps {
  topology: TopologyData;
  telemetry?: any;
}

export function DependencyGraph({ topology, telemetry }: DependencyGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selected, setSelected] = useState<ServiceNode | null>(null);
  // Track active chaos events fetched independently
  const [activeChaosEvents, setActiveChaosEvents] = useState<any[]>([]);

  // Poll active chaos events
  useEffect(() => {
    const fetchChaos = async () => {
      try {
        const events = await apiService.getActiveChaosEvents();
        setActiveChaosEvents(Array.isArray(events) ? events : []);
      } catch {
        setActiveChaosEvents([]);
      }
    };
    fetchChaos();
    const interval = setInterval(fetchChaos, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!topology?.nodes) return;

    // Active chaos event details
    const chaosEvent = activeChaosEvents[0] ?? null;
    const chaosTarget  = chaosEvent?.target_service?.toLowerCase() ?? null;
    const chaosType    = chaosEvent?.event_type?.toLowerCase() ?? null;

    const chaosElapsed = chaosEvent
      ? (Date.now() - new Date(chaosEvent.start_time).getTime()) / 1000
      : 0;

    const chaosIntensity = (maxSeconds: number): number =>
      Math.min((chaosElapsed / maxSeconds) * 100, 95);

    // Compute load score per service
    const getLoadPercent = (nodeId: string): number => {
      const name = nodeId.toLowerCase();
      const metrics  = telemetry?.metrics  || {};
      const pvcs: any[] = telemetry?.pvc_metrics || [];

      // Chaos-driven overrides
      if (chaosTarget === name || (name === 'database' && chaosTarget === 'database')) {
        switch (chaosType) {
          case 'cpu':
          case 'memory':
            return chaosIntensity(120);
          case 'storage':
            if (name === 'database') return chaosIntensity(150);
            break;
          case 'network':
            return Math.min(chaosIntensity(90), 70);
          case 'pod_crash':
            return 100;
        }
      }

      // Database PVC usage
      if (name === 'database') {
        const pg = pvcs.filter((p: any) =>
          (p.pvc_name || '').toLowerCase().includes('postgres')
        );
        if (pg.length === 0) return 0;
        return Math.max(...pg.map((p: any) => p.percentage_used ?? 0));
      }

      // Standard service pods load
      const matchKeys = Object.keys(metrics).filter(k =>
        k.toLowerCase().startsWith(name)
      );
      if (matchKeys.length === 0) return 0;

      const totalCores = matchKeys.reduce(
        (sum, k) => sum + (metrics[k]?.cpu_cores ?? 0), 0
      );
      const cpuLoad = Math.min(totalCores * 100, 100);

      const totalMemMb = matchKeys.reduce(
        (sum, k) => sum + (metrics[k]?.memory_mb ?? 0), 0
      );
      const memLoad = Math.min((totalMemMb / 1024) * 100, 100);

      return Math.max(cpuLoad, memLoad);
    };

    // Edge styles based on traffic and chaos
    const getEdgeStyle = (source: string, target: string) => {
      if (
        chaosType === 'network' &&
        (chaosTarget === source || chaosTarget === target)
      ) {
        return { color: '#EF4444', width: 3 };
      }
      if (
        chaosType === 'pod_crash' &&
        (chaosTarget === source || chaosTarget === target)
      ) {
        return { color: '#EF4444', width: 3 };
      }

      const link = (telemetry?.net_metrics || []).find(
        (l: any) => l.source_service === source && l.target_service === target
      );
      if (!link) return { color: '#14B8A6', width: 2 };
      if (link.latency_ms > 500 || link.packet_loss_rate > 5)
        return { color: '#EF4444', width: 3 };
      if (link.latency_ms > 150 || link.packet_loss_rate > 1)
        return { color: '#F97316', width: 2.5 };
      return { color: '#14B8A6', width: 2 };
    };

    // Node status derivation
    const getNodeStatus = (n: ServiceNode): 'active' | 'warning' | 'error' => {
      const name = n.id.toLowerCase();
      if (chaosTarget === name) {
        const load = getLoadPercent(name);
        if (load >= 85 || chaosType === 'pod_crash') return 'error';
        if (load >= 40) return 'warning';
      }
      return n.status;
    };

    const flowNodes = topology.nodes.map(n => ({
      id: n.id,
      type: 'service',
      position: POSITIONS[n.id] || { x: 100, y: 100 },
      data: {
        label:       n.id,
        status:      getNodeStatus(n),
        pods:        n.pods,
        fullName:    n.full_name,
        cpuCores:    telemetry?.metrics?.[n.id]?.cpu_cores,
        memoryMb:    telemetry?.metrics?.[n.id]?.memory_mb,
        loadPercent: getLoadPercent(n.id),
        chaosType:   chaosTarget === n.id.toLowerCase() ? chaosType : null,
      },
    }));

    const flowEdges = (topology.edges || []).map((e, i) => {
      const es = getEdgeStyle(e.source, e.target);
      return {
        id: `e-${i}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed, color: es.color, width: 16, height: 16 },
        style: { stroke: es.color, strokeWidth: es.width },
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [topology, telemetry, activeChaosEvents]);

  const onNodeClick = useCallback((_: any, node: any) => {
    const found = topology?.nodes?.find(n => n.id === node.id);
    setSelected(found || null);
  }, [topology]);

  const cpuInfo = selected ? telemetry?.metrics?.[selected.id] : null;
  const netLinks = selected ? telemetry?.net_metrics?.filter((l: any) => l.source_service === selected.id || l.target_service === selected.id) : [];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="page-header-title">Service Dependency Graph</h2>
          <p className="page-header-subtitle">Real-time Kubernetes service topology and health visualization</p>
        </div>
        <div className="flex items-center gap-3 text-xs font-500 text-surface-400">
          {[
            { color: 'bg-success-500', label: 'Healthy'  },
            { color: 'bg-warning-500', label: 'Warning'  },
            { color: 'bg-danger-600',  label: 'Critical' },
          ].map(l => (
            <span key={l.label} className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${l.color}`} />
              {l.label}
            </span>
          ))}
          {activeChaosEvents.length > 0 && (
            <span className="flex items-center gap-1.5 px-2 py-0.5 bg-red-50 border border-red-200 rounded-full">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-red-600 font-600">
                Chaos: {activeChaosEvents[0].event_type} on {activeChaosEvents[0].target_service}
              </span>
            </span>
          )}
        </div>
      </div>

      <div className="solid-card overflow-hidden" style={{ height: 'calc(100vh - 220px)', minHeight: 560 }}>
        {topology?.nodes?.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-surface-300">
            <Network className="h-12 w-12 mb-3" />
            <p className="font-500">Loading dependency graph...</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#CBD5E1" gap={24} size={1} />
            <Controls />
          </ReactFlow>
        )}
      </div>

      {/* Sidebar Drawer */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.25 }}
            className="solid-card p-6"
          >
            <div className="flex items-start justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-brand-50 rounded-xl">
                  <Server className="h-5 w-5 text-brand-600" />
                </div>
                <div>
                  <h3 className="text-base font-700 text-surface-900 capitalize">{selected.id} Service</h3>
                  <p className="text-xs text-surface-400">{selected.full_name}</p>
                </div>
              </div>
              <button onClick={() => setSelected(null)} className="p-2 rounded-xl hover:bg-surface-100 transition-colors">
                <X className="h-4 w-4 text-surface-400" />
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-50 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2"><Cpu className="h-4 w-4 text-brand-400" /><span className="text-xs font-600 text-surface-500">CPU</span></div>
                <p className="text-lg font-700 text-surface-900">{cpuInfo?.cpu_cores?.toFixed(4) || '—'}</p>
                <p className="text-xs text-surface-400">cores</p>
              </div>
              <div className="bg-surface-50 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2"><HardDrive className="h-4 w-4 text-purple-400" /><span className="text-xs font-600 text-surface-500">Memory</span></div>
                <p className="text-lg font-700 text-surface-900">{cpuInfo?.memory_mb?.toFixed(0) || '—'}</p>
                <p className="text-xs text-surface-400">MB</p>
              </div>
              <div className="bg-surface-50 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2"><Network className="h-4 w-4 text-cyan-500" /><span className="text-xs font-600 text-surface-500">Network Links</span></div>
                <p className="text-lg font-700 text-surface-900">{netLinks.length}</p>
                <p className="text-xs text-surface-400">connections</p>
              </div>
              <div className="bg-surface-50 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2"><Server className="h-4 w-4 text-success-500" /><span className="text-xs font-600 text-surface-500">Pods</span></div>
                <p className="text-lg font-700 text-surface-900">{selected.pods}</p>
                <p className="text-xs text-surface-400">running</p>
              </div>
            </div>
            {netLinks.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-600 text-surface-500 uppercase tracking-wider mb-3">Network Links Involving This Service</p>
                <div className="space-y-2">
                  {netLinks.slice(0, 3).map((l: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-surface-50 rounded-xl text-xs">
                      <span className="font-600 text-surface-700">{l.source_service} → {l.target_service}</span>
                      <span className={`font-700 ${l.latency_ms > 500 ? 'text-danger-600' : 'text-success-600'}`}>{l.latency_ms.toFixed(0)}ms</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
