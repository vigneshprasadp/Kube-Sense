import { useState, useCallback, useEffect } from 'react';
import ReactFlow, { Background, Controls, MiniMap, useNodesState, useEdgesState, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Server, Network, Cpu, HardDrive } from 'lucide-react';
import { ServiceNodeComponent } from '../components/graph/ServiceNode';
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

  useEffect(() => {
    if (!topology?.nodes) return;

    const flowNodes = topology.nodes.map(n => ({
      id: n.id,
      type: 'service',
      position: POSITIONS[n.id] || { x: 100, y: 100 },
      data: {
        label: n.id,
        status: n.status,
        pods: n.pods,
        fullName: n.full_name,
        cpuCores: telemetry?.metrics?.[n.id]?.cpu_cores,
        memoryMb: telemetry?.metrics?.[n.id]?.memory_mb,
      },
    }));

    const flowEdges = (topology.edges || []).map((e, i) => ({
      id: `e-${i}-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#14B8A6', width: 16, height: 16 },
      style: { stroke: '#14B8A6', strokeWidth: 2 },
    }));

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [topology, telemetry]);

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
          {[{ color: 'bg-success-500', label: 'Healthy' }, { color: 'bg-warning-500', label: 'Warning' }, { color: 'bg-danger-600', label: 'Critical' }].map(l => (
            <span key={l.label} className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${l.color}`} />
              {l.label}
            </span>
          ))}
        </div>
      </div>

      <div className="solid-card overflow-hidden" style={{ height: 560 }}>
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
            <MiniMap nodeColor={(n) => {
              const st = n.data?.status;
              return st === 'active' ? '#16A34A' : st === 'warning' ? '#F59E0B' : '#DC2626';
            }} />
          </ReactFlow>
        )}
      </div>

      {/* Node Drawer */}
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
