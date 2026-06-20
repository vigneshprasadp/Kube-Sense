import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  icon: ReactNode;
  iconBg?: string;
  valueColor?: string;
  subtitle?: string;
  index?: number;
}

export function MetricCard({
  label,
  value,
  unit,
  icon,
  iconBg = 'bg-brand-50 text-brand-600',
  valueColor = 'text-surface-900',
  subtitle,
  index = 0,
}: MetricCardProps) {
  return (
    <motion.div
      className="solid-card p-6 flex flex-col gap-3"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.06 }}
    >
      <div className="flex items-start justify-between">
        <span className="metric-label">{label}</span>
        <div className={`p-2.5 rounded-xl ${iconBg}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className={`metric-value ${valueColor}`}>{value}</span>
        {unit && <span className="text-sm text-surface-400 font-medium">{unit}</span>}
      </div>
      {subtitle && (
        <p className="text-xs text-surface-400 font-medium">{subtitle}</p>
      )}
    </motion.div>
  );
}
