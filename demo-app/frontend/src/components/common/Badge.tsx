import type { Severity } from '../../types';

interface BadgeProps {
  severity: Severity | string;
  label?: string;
  size?: 'sm' | 'md';
}

const CONFIG: Record<string, { cls: string; dot: string }> = {
  Critical: { cls: 'badge-critical', dot: 'bg-danger-600' },
  Warning:  { cls: 'badge-warning',  dot: 'bg-warning-500' },
  Info:     { cls: 'badge-info',     dot: 'bg-brand-600' },
  Success:  { cls: 'badge-success',  dot: 'bg-success-600' },
  Purple:   { cls: 'badge-purple',   dot: 'bg-purple-600' },
};

export function Badge({ severity, label, size = 'md' }: BadgeProps) {
  const cfg = CONFIG[severity] || CONFIG.Info;
  return (
    <span className={`badge ${cfg.cls} ${size === 'sm' ? 'text-[10px] py-0.5 px-2' : ''}`}>
      <span className={`status-dot ${cfg.dot} !w-1.5 !h-1.5`} />
      {label || severity}
    </span>
  );
}
