import { Handle, Position } from 'reactflow';
import { Server, Database, Layout, Activity } from 'lucide-react';

interface ServiceNodeData {
  label: string;
  status: 'active' | 'warning' | 'error';
  pods?: number;
  fullName?: string;
  cpuCores?: number;
  memoryMb?: number;
}

const ICON_MAP: Record<string, any> = {
  frontend:   Layout,
  backend:    Server,
  database:   Database,
  prometheus: Activity,
};

const STATUS_CONFIG = {
  active:  { ring: 'ring-success-500/30', badge: 'bg-success-500', label: 'Healthy',  text: 'text-success-600',  bg: 'bg-success-50' },
  warning: { ring: 'ring-warning-500/30', badge: 'bg-warning-500', label: 'Warning',  text: 'text-warning-600',  bg: 'bg-warning-50' },
  error:   { ring: 'ring-danger-600/30',  badge: 'bg-danger-600',  label: 'Critical', text: 'text-danger-600',   bg: 'bg-danger-50' },
};

const NODE_COLORS: Record<string, { from: string; to: string; iconBg: string }> = {
  frontend:   { from: '#F0FDFA', to: '#CCFBF1', iconBg: 'bg-brand-100 text-brand-700' },
  backend:    { from: '#F0FDF4', to: '#DCFCE7', iconBg: 'bg-success-100 text-success-700' },
  database:   { from: '#F5F3FF', to: '#EDE9FE', iconBg: 'bg-purple-100 text-purple-700' },
  prometheus: { from: '#FFF7ED', to: '#FFEDD5', iconBg: 'bg-orange-100 text-orange-700' },
};

export function ServiceNodeComponent({ data }: { data: ServiceNodeData }) {
  const Icon = ICON_MAP[data.label?.toLowerCase()] || Server;
  const s = STATUS_CONFIG[data.status] || STATUS_CONFIG.active;
  const c = NODE_COLORS[data.label?.toLowerCase()] || NODE_COLORS.backend;

  return (
    <div
      className={`ring-2 ${s.ring} rounded-2xl shadow-card bg-white border border-surface-200 min-w-[160px] transition-all hover:shadow-card-hover`}
      style={{ background: `linear-gradient(135deg, ${c.from}, ${c.to})` }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#0D9488', width: 8, height: 8, border: '2px solid white' }} />

      <div className="p-4">
        <div className="flex items-center gap-2.5 mb-3">
          <div className={`p-2 rounded-xl ${c.iconBg}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-700 text-surface-800 capitalize leading-tight">{data.label}</p>
            <p className="text-[10px] text-surface-400 truncate max-w-[90px]">{data.fullName}</p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg ${s.bg}`}>
            <span className={`status-dot ${s.badge} !w-1.5 !h-1.5`} />
            <span className={`text-[10px] font-600 ${s.text}`}>{s.label}</span>
          </div>
          {data.pods !== undefined && (
             <span className="text-[10px] text-surface-400 font-500">{data.pods} pod{data.pods !== 1 ? 's' : ''}</span>
          )}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: '#0D9488', width: 8, height: 8, border: '2px solid white' }} />
    </div>
  );
}
