import { Handle, Position } from 'reactflow';
import { Server, Database, Layout, Activity } from 'lucide-react';

interface ServiceNodeData {
  label: string;
  status: 'active' | 'warning' | 'error';
  pods?: number;
  fullName?: string;
  cpuCores?: number;
  memoryMb?: number;
  // 0–100 load score derived from CPU / memory / PVC usage
  loadPercent?: number;
  // Active chaos type targeting this node (null = none)
  chaosType?: string | null;
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

/** Interpolate between two hex colours by ratio [0..1] */
function lerpColor(a: string, b: string, t: number): string {
  const hex = (s: string) => [
    parseInt(s.slice(1, 3), 16),
    parseInt(s.slice(3, 5), 16),
    parseInt(s.slice(5, 7), 16),
  ];
  const [ar, ag, ab] = hex(a);
  const [br, bg, bb] = hex(b);
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg - ag) * t);
  const bl = Math.round(ab + (bb - ab) * t);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${bl.toString(16).padStart(2, '0')}`;
}

/** Return gradient stops based on load 0–100 */
function getLoadGradient(
  label: string,
  loadPercent: number,
): { from: string; to: string; iconBg: string; ring: string; pulseGlow: boolean } {
  const name = label?.toLowerCase();

  // Base (idle) colours per service
  const BASE: Record<string, { from: string; to: string; iconBg: string }> = {
    frontend:   { from: '#F0FDFA', to: '#CCFBF1', iconBg: 'bg-brand-100 text-brand-700' },
    backend:    { from: '#F0FDF4', to: '#DCFCE7', iconBg: 'bg-success-100 text-success-700' },
    database:   { from: '#F5F3FF', to: '#EDE9FE', iconBg: 'bg-purple-100 text-purple-700' },
    prometheus: { from: '#FFF7ED', to: '#FFEDD5', iconBg: 'bg-orange-100 text-orange-700' },
  };

  // Hot (saturated) colours — deep red / crimson
  const HOT_FROM = '#FFF1F2'; // rose-50
  const HOT_TO   = '#FFE4E6'; // rose-100 mid
  const CRIT_FROM = '#FEE2E2'; // red-100
  const CRIT_TO   = '#FECACA'; // red-200

  const base = BASE[name] || BASE.backend;

  if (loadPercent < 30) {
    // Idle → no change
    return { ...base, ring: 'ring-success-400/30', pulseGlow: false };
  }

  if (loadPercent < 60) {
    // Mild load → interpolate toward warm amber
    const t = (loadPercent - 30) / 30;
    return {
      from: lerpColor(base.from, '#FFFBEB', t),
      to:   lerpColor(base.to,   '#FEF3C7', t),
      iconBg: 'bg-amber-100 text-amber-700',
      ring: 'ring-warning-400/40',
      pulseGlow: false,
    };
  }

  if (loadPercent < 85) {
    // High load → orange-red
    const t = (loadPercent - 60) / 25;
    return {
      from: lerpColor('#FFFBEB', HOT_FROM, t),
      to:   lerpColor('#FEF3C7', HOT_TO, t),
      iconBg: 'bg-orange-100 text-orange-700',
      ring: 'ring-orange-500/50',
      pulseGlow: loadPercent > 75,
    };
  }

  // Critical → deep red + pulse glow
  return {
    from: CRIT_FROM,
    to:   CRIT_TO,
    iconBg: 'bg-red-100 text-red-700',
    ring: 'ring-red-500/60',
    pulseGlow: true,
  };
}

/** Small load bar shown at bottom of node */
function LoadBar({ load }: { load: number }) {
  const color =
    load < 30 ? '#22C55E' :
    load < 60 ? '#F59E0B' :
    load < 85 ? '#F97316' :
               '#EF4444';
  return (
    <div className="mt-3 px-1">
      <div className="flex justify-between text-[9px] font-600 mb-0.5" style={{ color }}>
        <span>Load</span>
        <span>{load.toFixed(0)}%</span>
      </div>
      <div className="h-1 bg-black/10 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.min(load, 100)}%`, background: color }}
        />
      </div>
    </div>
  );
}

const CHAOS_LABELS: Record<string, string> = {
  cpu:       'CPU ↑',
  memory:    'Mem ↑',
  storage:   'PVC ↑',
  network:   'Net ↑',
  pod_crash: 'Crashed',
};

export function ServiceNodeComponent({ data }: { data: ServiceNodeData }) {
  const Icon = ICON_MAP[data.label?.toLowerCase()] || Server;
  const s = STATUS_CONFIG[data.status] || STATUS_CONFIG.active;
  const load = data.loadPercent ?? 0;
  const c = getLoadGradient(data.label, load);
  const chaosLabel = data.chaosType ? CHAOS_LABELS[data.chaosType] : null;

  return (
    <div
      className={`ring-2 ${c.ring} rounded-2xl shadow-card bg-white border border-surface-200 min-w-[160px] transition-all duration-700 hover:shadow-card-hover ${c.pulseGlow ? 'animate-pulse' : ''}`}
      style={{ background: `linear-gradient(135deg, ${c.from}, ${c.to})` }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#0D9488', width: 8, height: 8, border: '2px solid white' }} />

      <div className="p-4">
        <div className="flex items-center gap-2.5 mb-3">
          <div className={`p-2 rounded-xl ${c.iconBg}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <p className="text-sm font-700 text-surface-800 capitalize leading-tight">{data.label}</p>
              {chaosLabel && (
                <span className="text-[9px] font-800 px-1.5 py-0.5 bg-red-500 text-white rounded-md leading-none">
                  {chaosLabel}
                </span>
              )}
            </div>
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

        {/* Load bar — only shown when there is meaningful load */}
        {load > 5 && <LoadBar load={load} />}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: '#0D9488', width: 8, height: 8, border: '2px solid white' }} />
    </div>
  );
}
